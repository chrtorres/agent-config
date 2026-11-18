#!/usr/bin/env python3
"""Run a retained, multi-shape smoke test for the required interactive viewer."""

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "interactive-review-viewer"
GENERATOR = SKILL_DIR / "scripts" / "smoke_model_generator.py"
LAUNCHER = SKILL_DIR / "scripts" / "launch_interactive_viewer.py"
SHAPES = ("cube", "sphere", "cylinder", "cone", "torus", "ico")
STYLES = ("soft", "left", "right", "rim", "top", "cross")


def find_executable(names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def check(condition, label, results):
    if not condition:
        raise RuntimeError(f"FAIL {label}")
    results.append(f"PASS {len(results) + 1} {label}")


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_http(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox", required=True, help="new or existing retained sandbox directory")
    parser.add_argument("--blender", default=None)
    parser.add_argument("--chrome", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--min-checks", type=int, default=20)
    parser.add_argument("--cleanup-approved", action="store_true", help="delete only a marked sandbox after the run")
    args = parser.parse_args()

    sandbox = Path(args.sandbox).expanduser().resolve()
    marker = sandbox / ".interactive-review-smoke-sandbox"
    if args.cleanup_approved:
        if not marker.is_file() or sandbox == Path("/") or len(sandbox.parts) < 4:
            raise SystemExit("Refusing cleanup: sandbox marker or safe path check failed")
        shutil.rmtree(sandbox)
        print(f"Cleaned approved smoke-test sandbox: {sandbox}")
        return

    blender = args.blender or find_executable(("blender",))
    chrome = args.chrome or find_executable(("google-chrome", "chromium", "chromium-browser"))
    if not blender:
        raise SystemExit("Blender is required")
    if not chrome:
        raise SystemExit("A Chromium-compatible browser is required for rendered smoke checks")
    sandbox.mkdir(parents=True, exist_ok=True)
    marker.write_text("Retained interactive-review smoke-test sandbox. Cleanup requires --cleanup-approved.\n")
    results = []
    metadata_template = json.loads((TEMPLATE_DIR / "metadata.json").read_text())

    for shape, style in zip(SHAPES, STYLES):
        review = sandbox / shape
        review.mkdir(exist_ok=True)
        for item in TEMPLATE_DIR.iterdir():
            destination = review / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
        metadata = dict(metadata_template)
        metadata["facts"] = dict(metadata_template.get("facts", {}))
        metadata["facts"].update({"Shape": shape, "Shadow style": style})
        (review / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        with (review / "blender.log").open("w") as log:
            subprocess.run([blender, "--background", "--python", str(GENERATOR), "--", "--shape", shape, "--style", style, "--output", str(review)], check=True, stdout=log, stderr=subprocess.STDOUT)
        check((review / "model.blend").is_file(), f"{shape} Blender artifact", results)
        check((review / "preview.png").stat().st_size > 0, f"{shape} rendered preview", results)
        check((review / "model.glb").stat().st_size > 0, f"{shape} GLB export", results)
        check((review / "metadata.json").is_file(), f"{shape} metadata", results)

    port = args.port or available_port()
    server = subprocess.Popen([sys.executable, str(LAUNCHER), "--directory", str(sandbox), "--port", str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        check(wait_for_http(f"http://127.0.0.1:{port}/cube/"), "viewer server startup", results)
        for shape in SHAPES:
            base = f"http://127.0.0.1:{port}/{shape}/"
            for resource in ("", "model.glb", "metadata.json", "styles.css", "viewer.js"):
                with urllib.request.urlopen(base + resource, timeout=5) as response:
                    check(response.status == 200, f"HTTP 200 {shape}/{resource or 'index.html'}", results)
            screenshot = sandbox / shape / "browser.png"
            subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=6000", "--window-size=900,700", f"--screenshot={screenshot}", base], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            check(screenshot.stat().st_size > 0, f"browser render {shape}", results)
    finally:
        server.terminate()
        server.wait(timeout=5)

    check(len(results) >= args.min_checks, f"minimum check count {len(results)} >= {args.min_checks}", results)
    (sandbox / "smoke-results.txt").write_text("\n".join(results) + f"\nTOTAL_PASS={len(results)}\n")
    (sandbox / "README.md").write_text(f"# Interactive review smoke-test sandbox\n\nPassed checks: {len(results)}\n\nShapes: {', '.join(SHAPES)}\n\nShadow styles: {', '.join(STYLES)}\n\nThis sandbox is retained. Cleanup requires explicit user approval and `--cleanup-approved`.\n")
    print(f"TOTAL_PASS={len(results)}")
    print(f"SANDBOX={sandbox}")


if __name__ == "__main__":
    main()
