"""Serve bundled or supplied static assets on an OS-selected local port."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'assets/web-app')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory / 'index.html').is_file():
        parser.error('Static directory must contain index.html')
    server = ThreadingHTTPServer((args.host, args.port), partial(SimpleHTTPRequestHandler, directory=str(directory)))
    print(f'http://{args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
