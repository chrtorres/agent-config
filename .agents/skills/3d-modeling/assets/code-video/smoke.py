"""Verify synthetic MP4s through decoding, HTTP delivery, and Chromium playback."""

from argparse import ArgumentParser
from base64 import b64decode
from contextlib import contextmanager, suppress
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from re import fullmatch
from json import dumps, loads
from pathlib import Path
from subprocess import DEVNULL, Popen, check_output, run
from sys import executable
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
from urllib.request import Request, urlopen

from websocket import create_connection

from video import FPS, FRAMES, SIZE, inspect


def eventually(read, seconds=10):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        result = read()
        if result:
            return result
        sleep(0.05)
    raise AssertionError("Browser did not reach the expected state")


@contextmanager
def browser(executable):
    with TemporaryDirectory(prefix="gym-review-chrome-") as profile, Popen(
        [executable, "--headless", "--remote-debugging-port=0", f"--user-data-dir={profile}",
         "--autoplay-policy=no-user-gesture-required", "about:blank"],
        stdout=DEVNULL, stderr=DEVNULL,
    ) as process:
        try:
            endpoint = Path(profile) / "DevToolsActivePort"
            port = eventually(lambda: endpoint.read_text().splitlines()[0] if endpoint.is_file() else None)
            with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as request:
                address = loads(request.read())[0]["webSocketDebuggerUrl"]
            connection = create_connection(address, suppress_origin=True, timeout=10)
            try:
                yield connection
            finally:
                connection.close()
        finally:
            process.terminate()
            process.wait(timeout=10)


class Session:
    def __init__(self, socket):
        self.socket = socket
        self.message_id = 0

    def call(self, method, **params):
        self.message_id += 1
        self.socket.send(dumps({"id": self.message_id, "method": method, "params": params}))
        while True:
            result = loads(self.socket.recv())
            if result.get("id") == self.message_id:
                if "error" in result:
                    raise AssertionError(result["error"])
                return result["result"]

    def script(self, expression):
        result = self.call(
            "Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True,
        )
        if "exceptionDetails" in result:
            raise AssertionError(result["exceptionDetails"])
        return result["result"].get("value")


def byte_range(header, length):
    match = fullmatch(r"bytes=(\d{0,20})-(\d{0,20})", header)
    if not match or not any(match.groups()):
        raise ValueError("Expected one byte range")
    start, end = match.groups()
    if not start:
        first, last = max(0, length - int(end)), length - 1
    else:
        first, last = int(start), min(length - 1, int(end)) if end else length - 1
    if first > last:
        raise ValueError("The requested range is outside the media")
    return first, last


def handler_for(directory):
    files = {"/" + path.name: path for path in directory.glob("*.mp4")}

    class ReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                page = (directory / "index.html").read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page)
            elif self.path in files:
                self.serve_video(files[self.path])
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def serve_video(self, path):
            try:
                source = path.open("rb")
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND, "Video file unavailable")
                return
            with source:
                length = source.seek(0, 2)
                header = self.headers.get("Range")
                if header is None:
                    first, last = 0, length - 1
                    self.send_response(HTTPStatus.OK)
                else:
                    try:
                        first, last = byte_range(header, length)
                    except ValueError:
                        self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                        self.send_header("Content-Range", f"bytes */{length}")
                        self.end_headers()
                        return
                    self.send_response(HTTPStatus.PARTIAL_CONTENT)
                    self.send_header("Content-Range", f"bytes {first}-{last}/{length}")
                remaining = last - first + 1
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(remaining))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                source.seek(first)
                # Browsers can close a request when the user seeks elsewhere.
                with suppress(BrokenPipeError, ConnectionResetError):
                    while remaining and (block := source.read(min(65536, remaining))):
                        self.wfile.write(block)
                        remaining -= len(block)

    return ReviewHandler


@contextmanager
def serve(directory):
    handler = handler_for(directory)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/"
        finally:
            server.shutdown()
            thread.join()


def check_browser(session, url, directory, require):
    session.call("Emulation.setDeviceMetricsOverride", width=750, height=380, deviceScaleFactor=1, mobile=False)
    session.call("Page.navigate", url=url)
    videos = "Array.from(document.querySelectorAll('video'))"
    eventually(lambda: session.script(
        f"{videos}.length === 2 && {videos}.every(v => v.readyState >= 2)"
    ))
    require("two usable media controls", session.script(f"{videos}.every(v => v.controls)"))
    require("both browser streams have expected dimensions", session.script(
        f"{videos}.every(v => v.videoWidth === {SIZE[0]} && v.videoHeight === {SIZE[1]})"
    ))
    require("both browser durations equal two seconds", session.script(
        f"{videos}.every(v => Math.abs(v.duration - 2) < .001)"
    ))
    result = session.script("""(async () => {
      const videos = Array.from(document.querySelectorAll('video'));
      const canvas = document.createElement('canvas');
      canvas.width = videos[0].videoWidth;
      canvas.height = videos[0].videoHeight;
      const ctx = canvas.getContext('2d', {willReadFrequently: true});
      const pixels = video => {
        ctx.drawImage(video, 0, 0);
        return ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      };
      const first = pixels(videos[0]);
      await Promise.all(videos.map(v => new Promise(resolve => {
        v.addEventListener('seeked', resolve, {once: true});
        v.currentTime = 1;
      })));
      const seek = videos.every(v => Math.abs(v.currentTime - 1) < .001 && !v.seeking);
      const left = pixels(videos[0]), right = pixels(videos[1]);
      return {seek, equal: left.every((b, i) => b === right[i]),
              changed: left.some((b, i) => b !== first[i])};
    })()""")
    require("both videos seek to time one", result["seek"])
    require("displayed scene changes after seek", result["changed"])
    require("displayed frames match after seek", result["equal"])
    directory.joinpath("browser.png").write_bytes(b64decode(
        session.call("Page.captureScreenshot", format="png")["data"],
    ))
    require("play and pause advance the native player", session.script("""(async () => {
      const video = document.querySelector('video');
      video.muted = true;
      await video.play();
      await new Promise(resolve => {
        video.addEventListener('timeupdate', resolve, {once: true});
      });
      video.pause();
      return video.paused && video.currentTime > 1;
    })()"""))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--chrome", required=True)
    args = parser.parse_args()
    args.output.mkdir()
    output = args.output.resolve()
    script = Path(__file__).with_name("video.py")
    checked = []

    def require(label, value):
        if not value:
            raise AssertionError(label)
        checked.append(label)

    def video(*arguments, **options):
        return run([executable, "-B", script, *arguments], **options)

    first, copied, spatial = [output / name for name in ("generated.mp4", "remuxed.mp4", "spatial.mp4")]
    video("generate", first, check=True)
    video("remux", first, copied, check=True)
    video("generate", spatial, "--frames-dir", args.frames_dir, check=True)
    report, clone, scene = map(inspect, (first, copied, spatial))
    for name, details, count in (("2D", report, FRAMES), ("3D", scene, 12)):
        image, audio = details["video"], details["audio"]
        require(f"{name} frame count", image["frames"] == count)
        require(f"{name} picture dimensions", (image["width"], image["height"]) == SIZE)
        require(f"{name} frame rate", image["rate"] == str(FPS))
        require(f"{name} motion", image["distinct_images"] == count)
        require(f"{name} starts at zero", image["timestamps"][0] == "0")
        require(f"{name} audio track", audio["codec"] == "aac" and audio["channels"] == 1)
        require(f"{name} audio sample clock", audio["rate"] == 48000 and audio["timestamps"][0] == "0")
    require("remux preserves encoded streams, decoded data and timing", report == clone)
    negative = video("inspect", first, "--compare", spatial, text=True, capture_output=True)
    require("comparison rejects a different synthetic clip", negative.returncode == 1 and "differ" in negative.stderr)
    output.joinpath("index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><link rel="icon" href="data:,"><title>Synthetic video review</title>'
        '<h1>Synthetic video review</h1>'
        '<video aria-label="Generated animation" controls width="320" src="generated.mp4"></video> '
        '<video aria-label="Sample-preserving remux" controls width="320" src="remuxed.mp4"></video></html>',
        encoding="utf-8",
    )
    with serve(output) as url:
        for clip in (first, copied, spatial):
            with urlopen(url + clip.name, timeout=5) as response:
                require(f"HTTP returns exact bytes for {clip.name}", response.status == 200 and response.read() == clip.read_bytes())
        request = Request(url + first.name, headers={"Range": "bytes=4-31"})
        with urlopen(request, timeout=5) as response:
            require("HTTP supports media byte ranges", response.status == 206 and response.read() == first.read_bytes()[4:32])
        with browser(args.chrome) as socket:
            check_browser(Session(socket), url, output, require)
    evidence = {
        "browser": check_output([args.chrome, "--version"], text=True).strip(),
        "passed": len(checked), "checks": checked,
        "container_bytes_equal": first.read_bytes() == copied.read_bytes(),
        "2d": report, "3d": scene,
    }
    output.joinpath("results.json").write_text(dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"{len(checked)} checks passed")


if __name__ == "__main__":
    main()
