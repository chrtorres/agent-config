#!/usr/bin/env python3
"""Serve a versioned interactive 3D review directory over HTTP."""

import argparse
import functools
import http.server
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, help="review directory containing index.html, model.glb, and metadata.json")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    directory = os.path.abspath(args.directory)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Serving interactive review from {directory} at http://127.0.0.1:{args.port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nReview server stopped.")


if __name__ == "__main__":
    main()
