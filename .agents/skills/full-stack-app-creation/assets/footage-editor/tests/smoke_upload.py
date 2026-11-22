"""Exercise the real editor when launched from Python without site packages."""
import argparse
from pathlib import Path
from selectors import DefaultSelector, EVENT_READ
import subprocess
import sys
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path, help="Short supported MP4 with a visible performer")
    parser.add_argument("--playwright", required=True, type=Path, help="Installed Playwright package directory")
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--dimensions", help="Expected native canvas width x height, e.g. 640x480")
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[1]
    if not (app / ".venv" / "bin" / "python").is_file():
        parser.error("Install the project's .venv first so the launch fallback can be exercised.")

    # -S reproduces a launch interpreter without the editor's installed packages.
    with subprocess.Popen([sys.executable, "-E", "-S", "-B", "run.py"], cwd=app, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, text=True) as server:
        try:
            with DefaultSelector() as startup:
                startup.register(server.stdout, EVENT_READ)
                if not startup.select(timeout=20):
                    raise RuntimeError("Editor did not report a URL within 20 seconds.")
                url = server.stdout.readline().strip()
            address = urlsplit(url)
            if address.hostname != "127.0.0.1" or not address.port:
                raise RuntimeError("Editor did not start on loopback. Check the launch output.")

            command = ["node", "tests/upload.mjs", url, str(args.playwright.resolve()),
                       str(args.browser.absolute()), str(args.fixture.resolve(strict=True))]
            if args.dimensions:
                command.append(args.dimensions)
            subprocess.run(command, cwd=app, check=True, timeout=420)
        finally:
            if server.poll() is None:
                server.terminate()
            server.communicate(timeout=30)


if __name__ == "__main__":
    main()
