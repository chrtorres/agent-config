#!/usr/bin/env python3
"""Loopback-only monitor. Explicit routes; no arbitrary commands or file access."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit, parse_qs
from monitor import Sampler, Jobs, PROFILES, GUIDANCE, demo_snapshot

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html"), "/style.css": ("style.css", "text/css"),
          "/app.mjs": ("app.mjs", "text/javascript"), "/core.mjs": ("core.mjs", "text/javascript")}


class MonitorServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address=("127.0.0.1", 0)):
        if address[0] != "127.0.0.1":
            raise ValueError("Only IPv4 loopback is supported")
        super().__init__(address, Handler)
        self.sampler, self.jobs = Sampler(), Jobs()
        self.demo_sequence = 0
        self.demo_lock = threading.Lock()

    def server_close(self):
        self.jobs.close()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Request paths and diagnostic data are not logged to disk.

    def reply(self, status, data, kind="application/json"):
        if kind == "application/json":
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted(self):
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host")
        origin = self.headers.get("Origin")
        return host in allowed and (not origin or origin == f"http://{host}") and self.headers.get("Sec-Fetch-Site") != "cross-site"

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {"error": "Local same-origin access required"})
        parsed = urlsplit(self.path)
        if parsed.path in ASSETS:
            file, kind = ASSETS[parsed.path]
            return self.reply(200, (WEB / file).read_bytes(), kind)
        if parsed.path == "/api/config":
            return self.reply(200, {"profiles": PROFILES, "guidance": GUIDANCE, "interval_seconds": 3})
        if parsed.path == "/api/snapshot":
            mode = parse_qs(parsed.query).get("mode", ["live"])[0]
            if mode == "demo":
                with self.server.demo_lock:
                    self.server.demo_sequence += 1
                    data = demo_snapshot(self.server.demo_sequence)
            elif mode == "live":
                data = self.server.sampler.snapshot()
            else:
                return self.reply(400, {"error": "Unknown data source"})
            return self.reply(200, data)
        if parsed.path == "/api/job":
            return self.reply(200, self.server.jobs.get())
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self.trusted():
            return self.reply(403, {"error": "Local same-origin access required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2048 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("Expected a JSON body, at most 2 KB")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected an object")
            if self.path == "/api/jobs":
                if set(data) != {"profile", "mode"} or not all(isinstance(v, str) for v in data.values()):
                    raise ValueError("Only a profile and data source are accepted")
                return self.reply(202, self.server.jobs.start(data["profile"], data["mode"]))
            if self.path == "/api/cancel":
                if set(data) != {"id"} or not isinstance(data["id"], str):
                    raise ValueError("Expected a job ID")
                return self.reply(200, self.server.jobs.cancel(data["id"]))
            return self.reply(404, {"error": "Not found"})
        except (ValueError, TypeError) as error:
            return self.reply(400, {"error": str(error)})
        except RuntimeError as error:
            return self.reply(409, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="Local port; default: choose a free port")
    args = parser.parse_args()
    server = MonitorServer(("127.0.0.1", args.port))
    print(f"System monitoring: http://127.0.0.1:{server.server_port}", flush=True)
    print("Read-only. Click Start monitoring or choose Demo in the dashboard. Ctrl+C stops the server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
