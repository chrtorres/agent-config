"""Behavioral recreation, not an iOS emulator. Python standard library only."""
import json
import os
from pathlib import Path
import tempfile
import urllib.request


TOOLS = []
for name, properties, required in [
    ('ls', {'path': {'type': 'string'}}, []),
    ('read', {'path': {'type': 'string'}}, ['path']),
    ('write', {'path': {'type': 'string'}, 'content': {'type': 'string'}}, ['path', 'content']),
    ('edit', {'path': {'type': 'string'}, 'oldText': {'type': 'string'}, 'newText': {'type': 'string'}}, ['path', 'oldText', 'newText']),
    ('find', {'pattern': {'type': 'string'}}, ['pattern']),
    ('grep', {'pattern': {'type': 'string'}}, ['pattern']),
]:
    TOOLS.append({'type': 'function', 'function': {'name': name, 'description': name + ' in the phone workspace',
                 'parameters': {'type': 'object', 'properties': properties, 'required': required}}})


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, path):
        candidate = Path(path)
        candidate = (candidate if candidate.is_absolute() else self.root / candidate).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError('Path is outside the workspace')
        return candidate

    def execute(self, name, args):
        spec = next((t['function'] for t in TOOLS if t['function']['name'] == name), None)
        if not spec:
            raise ValueError('Unknown tool: ' + name)
        for key in spec['parameters']['required']:
            if key not in args or not isinstance(args[key], str):
                raise ValueError('Missing or invalid argument: ' + key)
        if name == 'ls':
            return '\n'.join(sorted(p.name for p in self.resolve(args.get('path', '.')).iterdir()))
        if name == 'read':
            return self.resolve(args['path']).read_text()[:65536]
        if name in ('write', 'edit'):
            path = self.resolve(args['path'])
            if name == 'write':
                text = args['content']
            else:
                text = path.read_text()
                old = args['oldText']
                if not old or text.count(old) != 1:
                    raise ValueError('Edit must match exactly one region')
                text = text.replace(old, args['newText'], 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(dir=path.parent)
            try:
                with os.fdopen(fd, 'w') as output:
                    output.write(text)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            return 'Successfully changed ' + args['path']
        # Check every candidate: globbing must never permit a symlink escape.
        if name == 'find':
            return '\n'.join(str(p.relative_to(self.root)) for p in sorted(self.root.rglob(args['pattern']))
                             if self.resolve(str(p)).is_file())
        matches = []
        for path in sorted(self.root.rglob('*')):
            resolved = self.resolve(str(path))
            if resolved.is_file():
                try:
                    for number, line in enumerate(resolved.read_text().splitlines(), 1):
                        if args['pattern'] in line:
                            matches.append(f'{path.relative_to(self.root)}:{number}:{line}')
                except UnicodeDecodeError:
                    continue
        return '\n'.join(matches)[:65536]


class Agent:
    def __init__(self, workspace, base_url, model='scripted-model', api_key=None, confirm=True, approve=None):
        self.workspace = Workspace(workspace)
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = api_key
        self.confirm = confirm
        self.approve = approve or (lambda name, args: False)
        self.messages = [{'role': 'system', 'content': 'Work with the phone workspace using tools. Ask before changes.'}]
        self.events = []

    def request(self):
        payload = {'model': self.model, 'messages': self.messages, 'tools': TOOLS, 'stream': True}
        headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        req = urllib.request.Request(self.base_url + '/chat/completions', json.dumps(payload).encode(), headers)
        text, calls, done = '', {}, False
        with urllib.request.urlopen(req, timeout=15) as response:
            for raw in response:
                line = raw.decode().strip()
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data == '[DONE]':
                    done = True
                    break
                for choice in json.loads(data).get('choices', []):
                    delta = choice.get('delta', {})
                    text += delta.get('content') or ''
                    for fragment in delta.get('tool_calls', []):
                        index = fragment['index']
                        call = calls.setdefault(index, {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                        call['id'] += fragment.get('id', '')
                        fn = fragment.get('function', {})
                        call['function']['name'] += fn.get('name', '')
                        call['function']['arguments'] += fn.get('arguments', '')
        if not done:
            raise ValueError('Incomplete event stream: missing DONE')
        message = {'role': 'assistant', 'content': text or None}
        if calls:
            message['tool_calls'] = [calls[i] for i in sorted(calls)]
        return message

    def send(self, text, max_turns=12):
        self.messages.append({'role': 'user', 'content': text})
        for _ in range(max_turns):
            message = self.request()
            self.messages.append(message)
            calls = message.get('tool_calls', [])
            if not calls:
                return message['content'] or ''
            for call in calls:
                name = call['function']['name']
                try:
                    args = json.loads(call['function']['arguments'])
                    if not isinstance(args, dict):
                        raise ValueError('Tool arguments must be an object')
                    if name in ('write', 'edit') and self.confirm:
                        allowed = bool(self.approve(name, args))
                        self.events.append({'event': 'approval', 'tool': name, 'allowed': allowed})
                        if not allowed:
                            raise PermissionError('The user declined this change')
                    content = self.workspace.execute(name, args)
                    error = False
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    content, error = str(exc), True
                self.events.append({'event': 'tool', 'name': name, 'error': error, 'output': content})
                self.messages.append({'role': 'tool', 'tool_call_id': call['id'],
                                      'content': json.dumps({'isError': error, 'text': content})})
        raise RuntimeError('Agent turn limit exceeded')

    def save(self, path):
        Path(path).write_text(json.dumps({'messages': self.messages, 'events': self.events}, indent=2))

    def load(self, path):
        state = json.loads(Path(path).read_text())
        self.messages, self.events = state['messages'], state['events']
