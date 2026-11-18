#!/usr/bin/env python3
"""Loopback storage dashboard. No administrative or mutation endpoints."""
import argparse
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from telemetry import Collector, History, demo_history, demo_snapshot
from jit import SmartScan

ROOT = Path(__file__).resolve().parent
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
          "/core.mjs": ("core.mjs", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}


def make_server(port=0, data_dir=None):
    history = History(Path(data_dir or ROOT / ".runtime") / "history.sqlite3")
    collector = Collector(history)
    scan = SmartScan(collector)
    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "Atlas/1.0"

        def send(self, status, data, kind="application/json; charset=utf-8", attachment=False):
            content = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="atlas-storage-report.json"')
            self.end_headers()
            self.wfile.write(content)

        def valid_origin(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            return host in allowed and (not origin or origin == f"http://{host}")

        def do_GET(self):
            if not self.valid_origin():
                return self.send(403, {"error": "Only same-origin loopback access is allowed"})
            url = urlsplit(self.path)
            if self.path == "/api/session":
                return self.send(200, {"csrf": csrf})
            if self.path == "/api/smart-scan":
                return self.send(200, scan.status())
            if url.path in STATIC:
                file, mime = STATIC[url.path]
                return self.send(200, (ROOT / "web" / file).read_bytes(), mime)
            if url.path == "/api/health":
                return self.send(200, {"status": "ok", "service": "Atlas", "read_only": True})
            if url.path not in ("/api/snapshot", "/api/history", "/api/export"):
                return self.send(404, {"error": "Resource not found"})
            params = parse_qs(url.query, keep_blank_values=True)
            if set(params) - {"source"} or len(params.get("source", ["live"])) != 1:
                return self.send(400, {"error": "Expected a single source parameter"})
            source = params.get("source", ["live"])[0]
            if source not in ("live", "demo"):
                return self.send(400, {"error": "Source must be live or demo"})
            try:
                if url.path == "/api/history":
                    data = {"source": source, "samples": history.read() if source == "live" else demo_history()}
                else:
                    data = collector.snapshot() if source == "live" else demo_snapshot()
                    if url.path == "/api/export":
                        data = {"report": "Atlas storage inventory", "snapshot": data,
                                "history": history.read() if source == "live" else demo_history(),
                                "notes": ["Usage is known only for accessible mounted filesystems.",
                                          "No filesystems or drive contents have been changed."]}
                return self.send(200, data, attachment=url.path == "/api/export")
            except (RuntimeError, ValueError, OSError) as error:
                return self.send(503, {"error": str(error), "retryable": True})

        def do_POST(self):
            if self.path == "/api/smart-scan":
                if not self.valid_origin() or self.headers.get("Origin") != "http://" + self.headers.get("Host", "") or not secrets.compare_digest(self.headers.get("X-Atlas-CSRF", ""), csrf):
                    return self.send(403, {"error": "Same-origin user action required"})
                if self.headers.get("Content-Length", "0") != "0" or self.headers.get("Transfer-Encoding"):
                    return self.send(400, {"error": "This action accepts no input or passwords"})
                try:
                    scan.start()
                    return self.send(202, scan.status())
                except RuntimeError as error:
                    return self.send(409, {"error": str(error)})
            self.send(405, {"error": "This service is read-only"})

        def reject_write(self):
            self.send(405, {"error": "Unsupported method"})

        do_PUT = do_DELETE = do_PATCH = reject_write

        def log_message(self, fmt, *args):
            # No filesystem labels, host identity or query values in the access log.
            print(f"HTTP {self.command} {args[1] if len(args) > 1 else ''}", flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    server = make_server(args.port, args.data_dir)
    print(f"Atlas storage: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
