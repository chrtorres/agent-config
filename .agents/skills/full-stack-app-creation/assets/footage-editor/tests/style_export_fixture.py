"""Serve a prepared synthetic clip and one learned profile for browser export checks."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.serve import handler, upload_handler
from app.style_routes import Library
from tools.recording_style import analyse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path)
    parser.add_argument("work", type=Path, help="New directory for this fixture")
    args = parser.parse_args()
    args.work.mkdir()
    library = args.work / "library"
    Library(library).learn(analyse(args.clip), "Fictional camera")
    page = handler(args.work, args.clip)
    routes = upload_handler(args.work, None, page, style_setup={"library": library, "model": None})
    with ThreadingHTTPServer(("127.0.0.1", 0), routes) as server:
        print(f"http://{server.server_address[0]}:{server.server_port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
