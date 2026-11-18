#!/usr/bin/env python3
"""Capture checks and hashes outside reusable skills. No dependency installation."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def source_hashes(root):
    """Hash authored inputs, excluding dependency trees and generated evidence."""
    root = Path(root)
    paths = [root / name for name in ("server.py", "monitor.py", "README.md", "WORKFLOW.md", "package.json", "package-lock.json")]
    for name in ("web", "tests", "scripts", "objects"):
        paths.extend((root / name).rglob("*"))
    hashes = {}
    for file in sorted(paths):
        relative = file.relative_to(root)
        if file.is_file() and not {"node_modules", "__pycache__", ".venv", ".git", "evidence"}.intersection(relative.parts):
            hashes[str(relative)] = hashlib.sha256(file.read_bytes()).hexdigest()
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--live-host", action="store_true", help="Include authorized live-host observations in browser QA")
    parser.add_argument("--preview-url", help="Existing local server; otherwise a temporary one is started")
    args = parser.parse_args()
    if args.live_host and not args.browser:
        parser.error("--live-host requires --browser")
    if args.preview_url:
        target = urlsplit(args.preview_url)
        if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"} or target.username or target.password or target.path not in {"", "/"} or target.query or target.fragment:
            parser.error("Preview must be a plain local HTTP origin")
    output = args.output.resolve()
    if any((parent / "SKILL.md").is_file() for parent in (output, *output.parents)):
        parser.error("Evidence must be outside a shared skill directory")
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    python=sys.version, platform=platform.platform(), cwd=str(ROOT), commands=[], hashes={})
    server = None
    try:
        commands = [("node-version", ["node", "--version"]),
                    ("python-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]),
                    ("core-tests", ["node", "tests/test-core.mjs"]),
                    ("javascript-syntax", ["node", "--check", "web/app.mjs"])]
        if args.browser:
            origin = args.preview_url
            if not origin:
                server = subprocess.Popen([sys.executable, "-B", "server.py"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                with selectors.DefaultSelector() as selector:
                    selector.register(server.stdout, selectors.EVENT_READ)
                    if not selector.select(10):
                        raise RuntimeError("Preview did not start within 10 seconds")
                    line = server.stdout.readline().strip()
                if not line.startswith("System monitoring: http://127.0.0.1:"):
                    raise RuntimeError("Unexpected preview startup: " + line)
                origin = line.removeprefix("System monitoring: ")
            manifest["preview_url"] = origin
            commands.append(("browser-tests", ["node", "tests/browser-check.mjs", origin, str(output)] + (["--live-host"] if args.live_host else [])))
        for name, argv in commands:
            try:
                result = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False)
                code, log = result.returncode, result.stdout
            except (OSError, subprocess.TimeoutExpired) as error:
                code, log = -1, str(error)
            (output / f"{name}.txt").write_text(log)
            manifest["commands"].append(dict(name=name, argv=argv, cwd=str(ROOT), exit_code=code, log=f"{name}.txt"))
            print(f"{name}: {'PASS' if code == 0 else 'FAIL'}", flush=True)
        manifest["hashes"] = source_hashes(ROOT)
        manifest["passed"] = all(command["exit_code"] == 0 for command in manifest["commands"])
        manifest["browser_scope"] = ("live host and fixtures" if args.live_host else "fixture HTTP only") if args.browser else "Not run"
    except Exception as error:
        manifest.update(passed=False, error=str(error))
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        manifest["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    raise SystemExit(0 if manifest.get("passed") else 1)


if __name__ == "__main__":
    main()
