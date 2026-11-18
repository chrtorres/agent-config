"""Reproducible demonstration, or a CLI for a real OpenAI-compatible server."""
import argparse
import json
from pathlib import Path

from agent import Agent
from mock_server import MockServer, tool


def run_demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    workspace = output / 'phone' / 'Documents'
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / 'Welcome.md').write_text('Welcome to the simulated phone workspace.\n')
    turns = [tool('ls', path='.'), tool('read', path='Welcome.md'),
             tool('write', path='Notes/review.txt', content='The recreated agent wrote this file.\n'),
             tool('edit', path='Notes/review.txt', oldText='wrote', newText='created'),
             tool('read', path='Notes/review.txt'),
             tool('write', path='denied.txt', content='This must never be written.'),
             tool('write', path='../escape.txt', content='This must not escape.'),
             {'text': 'Read the welcome file, created and edited the note. Denied write and workspace escape were blocked.'}]
    decisions = []
    def approve(name, args):
        allowed = args.get('path') != 'denied.txt'
        decisions.append({'tool': name, 'path': args.get('path'), 'allowed': allowed})
        return allowed
    with MockServer(turns) as server:
        agent = Agent(workspace, server.base_url, approve=approve)
        answer = agent.send('Read my welcome note, create and edit a note, then exercise denied and out-of-workspace writes.')
        agent.save(output / 'conversation.json')
        (output / 'http_requests.json').write_text(json.dumps(server.requests, indent=2))
    checks = {
        'note_has_expected_content': (workspace / 'Notes/review.txt').read_text() == 'The recreated agent created this file.\n',
        'denied_file_absent': not (workspace / 'denied.txt').exists(),
        'escaped_file_absent': not (workspace.parent / 'escape.txt').exists(),
        'tool_results_returned_to_server': sum(m['role'] == 'tool' for m in server.requests[-1]['body']['messages']) == 7,
        'http_request_count': len(server.requests) == 8,
    }
    result = {'scope': 'Python behavioral recreation; no iOS execution; scripted server, no LLM',
              'answer': answer, 'approvals': decisions, 'checks': checks, 'passed': all(checks.values())}
    (output / 'demo_result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='evidence')
    parser.add_argument('--base-url', help='Use a real model server instead of the scripted demonstration')
    parser.add_argument('--model', help='Exact model ID served by the real endpoint')
    parser.add_argument('--workspace', default='workspace')
    args = parser.parse_args()
    if not args.base_url:
        run_demo(args.output)
        return
    if not args.model:
        parser.error('--model is required with --base-url')
    import os
    def approve(name, arguments):
        return input(f'Allow {name} {arguments.get("path")}? [y/N] ').lower() == 'y'
    agent = Agent(args.workspace, args.base_url, args.model, api_key=os.environ.get('MODEL_API_KEY'), approve=approve)
    while True:
        try:
            prompt = input('You (blank to exit): ')
        except EOFError:
            break
        if not prompt:
            break
        try:
            print('Agent:', agent.send(prompt))
        except Exception as exc:
            print(f'{type(exc).__name__}: {exc}')
    agent.save(Path(args.workspace).parent / 'session.json')


if __name__ == '__main__':
    main()
