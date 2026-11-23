"""Routes for a single volatile Face Swap job."""
from pathlib import Path
from contextlib import suppress
import json
import math
import re
from shutil import disk_usage, rmtree
from threading import Event, Lock
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from tools.progress import Estimate, read_progress


class FaceRoutes:
    def __init__(self, directory, build, file_handler, build_mask=None):
        self.directory = directory / "face-swap"
        self.build = build
        self.build_mask = build_mask
        self.lock = Lock()
        self.mask_lock = Lock()
        self.file_handler = file_handler
        self.job = None
        self.estimate = None
        self.ready = None
        self.result = None
        app = Path(__file__).resolve().parent
        self.page = file_handler({
            "/face-swap.mjs": app / "face-swap.mjs",
            "/face-swap/panel.html": app / "face-swap-panel.html",
            "/workspace.mjs": app / "workspace.mjs",
            "/viewer-size.mjs": app / "viewer-size.mjs",
            "/style.css": app / "style.css",
        })

    def cancel(self):
        with self.lock:
            if self.job is not None:
                self.job.set()
                return True
            return False

    def discard(self, cancel_active=True):
        with self.lock:
            if self.job is not None:
                if cancel_active:
                    self.job.set()
                return False
            if self.result is not None:
                self.result.retired.set()
            if self.directory.exists():
                rmtree(self.directory)
            self.ready = None
            self.result = None
            return True

    def status(self):
        with self.lock:
            phase = "idle"
            if self.ready is not None:
                phase = "ready"
            elif self.job is not None:
                phase = "cancelling" if self.job.is_set() else "processing"
            status = {"phase": phase, "report": self.ready}
            if phase == "processing":
                fraction, label = read_progress(self.directory / "progress")
                if label:
                    status["progress"] = label
                if self.estimate is not None:
                    status.update(self.estimate.snapshot(fraction))
        return status

    def get(self, request, body):
        path = urlsplit(request.path).path
        if path == "/face-swap/status" and body:
            request.reply(200, json.dumps(self.status()))
        elif path == "/face-swap/":
            request.send_response(302)
            request.send_header("Location", "/#face-swap")
            request.send_header("Cache-Control", "no-store")
            request.end_headers()
        elif path in ("/face-swap/result.mp4", "/face-swap/preview.mp4", "/face-swap/result.png"):
            with self.lock:
                result = self.result
            if result is not None:
                result.respond(request, body)
            else:
                request.send_error(404)
        else:
            self.page.respond(request, body)

    def post(self, request, prepared=None):
        if request.path == "/face-swap/mask":
            return self.mask(request)
        if request.path == "/face-swap/cancel":
            active = self.cancel()
            return request.reply(202 if active else 200, "Cancelling Face Swap." if active else "No Face Swap is running.")
        if request.path == "/face-swap/clear":
            try:
                if not self.discard(cancel_active=False):
                    return request.reply(409, "Cancel the running Face Swap first.")
            except OSError:
                return request.reply(500, "Could not clear the result. Stop the local editor to release its files.")
            return request.reply(200, "Face Swap cleared.")
        if request.path != "/face-swap/run":
            return request.reply(404, "Unknown Face Swap action.")
        if request.headers.get("Content-Type") != "application/octet-stream":
            return request.reply(415, "Choose a portrait and a target MP4.")
        fields = [request.headers.get(name, "") for name in
                  ("Content-Length", "X-Portrait-Bytes", "X-Source-Index", "X-Target-Index")]
        if not all(re.fullmatch(r"[0-9]{1,12}", field) for field in fields):
            return request.reply(400, "Invalid media sizes or face selection.")
        total, portrait, source_index, target_index = map(int, fields)
        selection = None
        if (point := request.headers.get("X-Target-Selection")) is not None:
            try:
                time, x, y = json.loads(point)
                if not all(type(value) in (int, float) and math.isfinite(value) for value in (time, x, y)):
                    raise ValueError()
                if time < 0 or not (0 <= x <= 1 and 0 <= y <= 1):
                    raise ValueError()
                selection = time, x, y
            except (TypeError, ValueError, OverflowError):
                return request.reply(400, "Select a point on the target video.")
        reuse_target = request.headers.get("X-Footage-Target") == "prepared"
        # A still image target is swapped once and returned as a verified PNG.
        image = request.headers.get("X-Target-Kind") == "image"
        if image and reuse_target:
            return request.reply(400, "The prepared editor target is a video.")
        if reuse_target and (prepared is None or not prepared.is_file()):
            return request.reply(409, "Open a target video in the editor first.")
        if not 0 < portrait <= total or (reuse_target != (portrait == total)) or portrait > 40 * 1024 ** 2:
            return request.reply(400, "Choose a portrait under 40 MB and a nonempty target MP4.")
        if image and total - portrait > 80 * 1024 ** 2:
            return request.reply(413, "Choose a target image under 80 MB.")
        try:
            needed = total + (prepared.stat().st_size if reuse_target else 0)
        except OSError:
            return request.reply(409, "The target video was cleared. Open it again.")
        with self.lock:
            if self.job is not None or self.ready is not None:
                return request.reply(409, "Clear the current result or cancel the active run first.")
            if needed >= disk_usage(self.directory.parent).free:
                return request.reply(413, "The inputs exceed available temporary memory.")
            self.directory.mkdir(mode=0o700)
            cancel = self.job = Event()
            self.estimate = Estimate()
        try:
            source = self.directory / "portrait"
            target = self.directory / ("target-image" if image else "target.mp4")

            def receive(path, remaining):
                with path.open("wb") as output:
                    while remaining and not cancel.is_set():
                        data = request.rfile.read(min(remaining, 1024 ** 2))
                        if not data:
                            raise ValueError("Upload interrupted. Try again.")
                        output.write(data)
                        remaining -= len(data)

            receive(source, portrait)
            if reuse_target:
                # Take a local copy so closing the main editor cannot invalidate an open render input.
                with prepared.open("rb") as original, target.open("wb") as copy:
                    while not cancel.is_set() and (block := original.read(1024 ** 2)):
                        copy.write(block)
            else:
                receive(target, total - portrait)
            if not cancel.is_set():
                if image:
                    self.build(source, target, self.directory, source_index, target_index, cancel, selection, image=True)
                else:
                    self.build(source, target, self.directory, source_index, target_index, cancel, selection)
            with self.lock:
                if cancel.is_set():
                    return request.reply(409, "Face Swap cancelled.")
                source.unlink()
                target.unlink()
                self.ready = json.loads((self.directory / "verification.json").read_text())
                self.ready["prepared_target"] = reuse_target
                self.result = self.file_handler({
                    "/face-swap/result.png": self.directory / "face-swap.png",
                } if image else {
                    "/face-swap/result.mp4": self.directory / "face-swap.mp4",
                    "/face-swap/preview.mp4": self.directory / "preview.mp4",
                })
            return request.reply(200, "Face Swap verified.")
        except (OSError, ValueError) as error:
            message = str(error) if isinstance(error, ValueError) else "Could not process these files in temporary memory."
            return request.reply(422, message)
        finally:
            with self.lock:
                if self.ready is None:
                    rmtree(self.directory, ignore_errors=True)
                self.job = None

    def mask(self, request):
        if self.build_mask is None:
            return request.reply(404, "Mask preview is unavailable.")
        try:
            length = int(request.headers.get("Content-Length", "0"))
            x, y = json.loads(request.headers.get("X-Target-Point", "null"))
            if not 0 < length <= 40 * 1024 ** 2 or not (0 <= x <= 1 and 0 <= y <= 1):
                raise ValueError()
        except (TypeError, ValueError):
            return request.reply(400, "Select a face on a readable target frame.")
        if request.headers.get("Content-Type") != "image/png":
            return request.reply(415, "The mask preview requires a PNG frame.")
        if not self.mask_lock.acquire(blocking=False):
            return request.reply(409, "Wait for the current mask, then select the face again.")
        try:
            curvature = request.headers.get("X-Face-Mask") == "curvature"
            with TemporaryDirectory(prefix="face-mask-", dir=self.directory.parent) as directory:
                work = Path(directory)
                data = request.rfile.read(length)
                if len(data) != length:
                    return request.reply(400, "The frame upload was interrupted.")
                frame, overlay = work / "frame.png", work / ("layers.json" if curvature else "mask.png")
                frame.write_bytes(data)
                if curvature:
                    self.build_mask(frame, overlay, x, y, True)
                else:
                    self.build_mask(frame, overlay, x, y)
                result = overlay.read_bytes()
            with suppress(BrokenPipeError, ConnectionResetError, TimeoutError):
                request.send_response(200)
                request.send_header("Content-Type", "application/json" if curvature else "image/png")
                request.send_header("Cache-Control", "no-store")
                request.send_header("Content-Length", str(len(result)))
                request.end_headers()
                request.wfile.write(result)
        except (OSError, ValueError) as error:
            message = str(error) if isinstance(error, ValueError) else "Unable to preview the selected mask."
            return request.reply(422, message)
        finally:
            self.mask_lock.release()
