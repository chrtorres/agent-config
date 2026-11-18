"""Deterministic OpenAI-compatible HTTP/SSE fixture. This is not an LLM."""
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


def tool(name, **args):
    return {'tool': name, 'args': args}


class MockServer:
    def __init__(self, turns):
        self.turns = list(turns)
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if self.path != '/v1/chat/completions':
                    self.send_error(404)
                    return
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append({'path': self.path, 'body': body, 'authorization': self.headers.get('Authorization')})
                turn = owner.turns.pop(0) if owner.turns else {'status': 500}
                if 'status' in turn:
                    self.send_error(turn['status'])
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()

                def emit(delta):
                    packet = {'choices': [{'index': 0, 'delta': delta}]}
                    self.wfile.write(('data: ' + json.dumps(packet) + '\n\n').encode())
                    self.wfile.flush()

                if 'tool' in turn or 'calls' in turn:
                    calls = turn.get('calls', [turn])
                    # Split argument JSON to exercise incremental tool-call reconstruction.
                    for i, call in enumerate(calls):
                        args = json.dumps(call.get('args', {}))
                        if 'raw_args' in call:
                            args = call['raw_args']
                        middle = len(args) // 2
                        emit({'tool_calls': [{'index': i, 'id': f'call_{len(owner.requests)}_{i}', 'type': 'function',
                              'function': {'name': call['tool'], 'arguments': args[:middle]}}]})
                        emit({'tool_calls': [{'index': i, 'function': {'arguments': args[middle:]}}]})
                else:
                    answer = turn.get('text', '')
                    for i in range(0, len(answer), 7):
                        emit({'content': answer[i:i + 7]})
                if not turn.get('truncate'):
                    self.wfile.write(b'data: [DONE]\n\n')

        self.http = ThreadingHTTPServer((socket.gethostbyname('localhost'), 0), Handler)
        self.thread = Thread(target=self.http.serve_forever, daemon=True)
        self.base_url = f'http://localhost:{self.http.server_port}/v1'

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
