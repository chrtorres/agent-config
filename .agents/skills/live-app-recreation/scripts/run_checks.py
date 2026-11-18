"""Validate bundled recreations and capture evidence outside the reusable skill."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', action='store_true', help='Also run browser checks; follow environment browser rules first')
    parser.add_argument('--preview-url', help='Use an already running preview for browser checks')
    args = parser.parse_args()
    skill = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output == skill or skill in output.parents:
        parser.error('Choose an evidence directory outside the reusable skill')
    if (output / 'demo').exists():
        parser.error('Demo output already exists; use a fresh evidence directory')
    output.mkdir(parents=True, exist_ok=True)
    records = []
    env = dict(os.environ, PYTHONPATH=str(skill / 'assets/python-agent'), PYTHONDONTWRITEBYTECODE='1')

    def run(label, command, cwd):
        if not command[0]:
            record = {'name': label, 'status': 'blocked', 'reason': 'Required runtime not found'}
        else:
            try:
                result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
                (output / (label + '.stdout.txt')).write_text(result.stdout)
                (output / (label + '.stderr.txt')).write_text(result.stderr)
                record = {'name': label, 'command': command, 'cwd': str(cwd), 'exit_code': result.returncode,
                          'status': 'pass' if result.returncode == 0 else 'fail'}
            except (OSError, subprocess.TimeoutExpired) as exc:
                record = {'name': label, 'status': 'blocked', 'reason': str(exc)}
        records.append(record)
        print(f'{label}: {record["status"]}', flush=True)

    with tempfile.TemporaryDirectory(prefix='live-app-check-') as work:
        run('python-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', str(skill / 'tests'), '-p', 'test_*.py', '-v'], work)
        demo = output / 'demo'
        run('python-demo', [sys.executable, str(skill / 'assets/python-agent/demo.py'), '--output', str(demo)], work)
        node = shutil.which('node')
        run('engine-tests', [node, str(skill / 'tests/test-engine.mjs')], work)
        run('app-syntax', [node, '--check', str(skill / 'assets/web-app/app.mjs')], work)
        if args.browser:
            server = None
            if args.preview_url:
                origin = args.preview_url
            else:
                handler = partial(SimpleHTTPRequestHandler, directory=str(skill / 'assets/web-app'))
                server = ThreadingHTTPServer(('localhost', 0), handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                origin = f'http://localhost:{server.server_port}'
            try:
                run('browser-tests', [node, str(skill / 'tests/browser-check.mjs'), origin, str(output / 'browser')], work)
            finally:
                if server:
                    server.shutdown()
                    server.server_close()
                    thread.join()
    manifest = {'scope': 'Bundled behavioral recreations; no native device or real LLM execution',
                'python': platform.python_version(), 'host': platform.platform(), 'checks': records,
                'source_sha256': {str(p.relative_to(skill)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for folder in ['assets', 'tests', 'scripts'] for p in sorted((skill / folder).rglob('*'))
                                  if p.is_file() and '__pycache__' not in p.parts}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return 0 if all(r['status'] == 'pass' for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
