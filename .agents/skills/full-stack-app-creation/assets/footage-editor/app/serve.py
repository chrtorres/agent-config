"""Serve the review and private footage assets over an ephemeral loopback port."""
from argparse import ArgumentParser
from contextlib import suppress
from errno import EAGAIN, EDQUOT, ENOMEM, ENOSPC
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import re
from shutil import copyfileobj, disk_usage, rmtree
from tempfile import TemporaryDirectory
from threading import Event, Lock, Thread
from time import monotonic
from urllib.parse import urlsplit


class PreviewOnly(ValueError):
    pass


class PreparationCancelled(ValueError):
    pass


class Job(Event):
    """A cancellable background task. Workers attach a progress tracker as they start."""
    stage = None
    tracker = None

    def progress(self):
        tracker = self.tracker
        return tracker.status() if tracker is not None else {"percent": None, "eta": None}


class UploadPreparation(Job):
    stage = "Receiving video"


def handler(assets, video=None, source=None, uhd=None, regions=None, skin=None, cleanup_tracks=None, motion_study=None,
            motion_splats=None, prepare_uhd=None, export_edit=None, source_extension="mp4"):
    app = Path(__file__).resolve().parent
    files = {"/": app/"index.html", "/4k/": app/"uhd.html"}
    modules = ("app.mjs","motion.mjs","render.mjs","regions.mjs","inspect.mjs","cleanup.mjs",
               "transport.mjs","secondary.mjs","splats.mjs","stage-zoom.mjs","picking.mjs","point-regions.mjs",
               "workspace.mjs","viewer-size.mjs","uhd.mjs","media-download.mjs","status.mjs","soft-body.mjs","colors.mjs",
               "style.mjs")
    files.update({"/"+name:app/name for name in (*modules,"style.css")})
    files["/video.mp4"]=video if video is not None else assets/"video.mp4"
    if source is not None:
        files["/source.mp4"]=source
    uhd = uhd if uhd is not None else assets/"4k.mp4"
    files["/4k.mp4"]=uhd
    timeline = assets/"timeline"
    files["/timeline/timeline.json"] = timeline/"timeline.json"
    if files["/timeline/timeline.json"].is_file():
        manifest = json.loads(files["/timeline/timeline.json"].read_text())
        for name, *_ in manifest["pages"]:
            if Path(name).name == name:
                files["/timeline/"+name] = timeline/name

    if regions is not None:
        files["/regions.json"]=regions
    if cleanup_tracks is not None:
        files["/cleanup-tracks.json"]=cleanup_tracks
    if motion_study is not None:
        files["/motion-study.json"]=motion_study
    if motion_splats is not None:
        files["/motion-splats.json"]=motion_splats
    if skin is not None:
        files.update({"/skin/"+p.name:p for p in skin.glob("skin-*.png") if p.is_file()})

    result = file_handler(files, source_extension)
    result.original_source = source
    result.editable_source = files["/video.mp4"]
    result.uhd = uhd
    result.prepare_uhd = staticmethod(prepare_uhd)
    result.export_edit = staticmethod(export_edit)
    return result


def upload_handler(directory, build, initial_editor=None, build_swap=None, build_mask=None, export_preview=None,
                   style_setup=None):
    app = Path(__file__).resolve().parent
    landing = file_handler({"/": app / "upload.html", "/upload.mjs": app / "upload.mjs",
                            "/style.css": app / "style.css", "/workspace.mjs": app / "workspace.mjs",
                            "/quick-review.mjs": app / "quick-review.mjs",
                            "/media-download.mjs": app / "media-download.mjs",
                            "/viewer-size.mjs": app / "viewer-size.mjs",
                            "/status.mjs": app / "status.mjs"})
    if build_swap is not None:
        from app.face_routes import FaceRoutes
        face = FaceRoutes(directory, build_swap, file_handler, build_mask)
    else:
        face = None
    if style_setup is not None:
        from app.style_routes import StyleRoutes
        style = StyleRoutes(directory, style_setup["library"], style_setup["model"], file_handler)
    else:
        style = None
    active = Lock()
    state = Lock()
    closing = Event()
    editor = initial_editor
    job = None
    uhd_job = None
    uhd_error = None
    uhd_attempt = 0
    export_job = None

    def status():
        """One snapshot of every background task, pushed to pages through /events."""
        with state:
            preparing, building, exporting, current = job, uhd_job, export_job, editor
            failure, attempt = uhd_error, uhd_attempt
        result = {"editor": current is not None}
        if preparing is None:
            result["preparation"] = {"phase": "idle"}
        else:
            result["preparation"] = {"phase": "cancelling" if preparing.is_set() else "preparing",
                                     "stage": preparing.stage, **preparing.progress()}
        if building is not None:
            result["uhd"] = {"phase": "building", **building.progress()}
        elif current is not None and current.uhd.is_file():
            result["uhd"] = {"phase": "ready"}
        else:
            result["uhd"] = {"phase": "failed", "message": failure} if failure else {"phase": "idle"}
        result["uhd"]["attempt"] = attempt
        result["export"] = {"phase": "rendering", "stage": exporting.stage, **exporting.progress()} \
            if exporting is not None else {"phase": "idle"}
        if face is not None:
            result["face"] = face.status()
        if style is not None:
            result["style"] = style.status()
        return result

    class Upload(landing):
        timeout = 30

        @classmethod
        def cancel_preparation(cls):
            with state:
                if job is None:
                    return False
                job.set()
                return True

        @classmethod
        def stop_jobs(cls):
            # Ends open status streams so the server can join their threads on exit.
            closing.set()
            cls.cancel_preparation()
            with state:
                if uhd_job is not None:
                    uhd_job.set()
                if export_job is not None:
                    export_job.set()
            if face is not None:
                face.cancel()
            if style is not None:
                style.cancel()

        def loopback_host(self):
            return f"127.0.0.1:{self.server.server_port}"

        def respond(self, body):
            # Private media must be served under the same loopback origin as the upload form.
            if self.headers.get("Host") != self.loopback_host():
                self.send_error(403)
                return
            if face is not None and (self.path.startswith("/face-swap/") or self.path == "/face-swap.mjs"):
                return face.get(self, body)
            if style is not None and self.path.startswith("/style/"):
                return style.get(self, body)
            if body and self.path == "/events":
                return self.events()
            if body and self.path == "/preparation":
                with state:
                    phase = ("cancelling" if job.is_set() else "preparing") if job is not None else "idle"
                    stage = job.stage if job is not None else None
                self.reply(200, phase, stage=stage)
                return
            if not body and self.path == "/clear":
                self.send_response(204)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            current = editor
            if current is None:
                super().respond(body)
            else:
                current.respond(self, body)

        def events(self):
            """Stream status changes as server-sent events instead of answering repeated polls."""
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(b"retry: 2000\n\n")
                last, sent = None, 0.
                while not closing.is_set():
                    payload = json.dumps(status(), separators=(",", ":"))
                    if payload != last:
                        self.wfile.write(b"data: " + payload.encode() + b"\n\n")
                        self.wfile.flush()
                        last, sent = payload, monotonic()
                    elif monotonic() - sent > 15:
                        # A comment keeps idle connections open through proxies and detects closed tabs.
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        sent = monotonic()
                    closing.wait(.5)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass
            self.close_connection = True

        def reply(self, status, message, preview=False, stage=None, attempt=None):
            body = message.encode("utf-8")
            with suppress(BrokenPipeError, ConnectionResetError, TimeoutError):
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                if preview:
                    self.send_header("X-Footage-Mode", "preview")
                if stage:
                    self.send_header("X-Footage-Stage", stage)
                if attempt is not None:
                    self.send_header("X-Footage-Attempt", str(attempt))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def edited_media(self, preview):
            nonlocal export_job
            value = self.headers.get("Content-Length", "")
            if not re.fullmatch(r"[0-9]{1,18}", value) or int(value) == 0:
                return self.reply(400, "Choose media or valid edit settings to download.")
            size = int(value)
            if size >= disk_usage(directory).free or (not preview and size > 262144):
                return self.reply(413, "The export input is too large for this session.")
            with state:
                current = editor
                if (preview and export_preview is None) or (not preview and (current is None or current.export_edit is None)):
                    return self.reply(404, "The edited media is unavailable in this session.")
                if export_job is not None or not active.acquire(blocking=False):
                    return self.reply(409, "Wait for the editor’s current task before downloading.")
                export_job = Job()
                export_job.stage = "Rendering Quick Review edits" if preview else "Rendering shape and color edits"
            try:
                with TemporaryDirectory(dir=directory) as scratch:
                    work = Path(scratch)
                    target = work / "edited.mp4"
                    if preview:
                        changes = json.loads(self.headers.get("X-Footage-Adjustments", "[]"))
                        bounds = ((1, 2), (.5, 1.5), (.5, 1.5), (0, 2))
                        if not isinstance(changes, list) or len(changes) != 4 or not all(
                                type(value) in (int, float) and low <= value <= high
                                for value, (low, high) in zip(changes, bounds)):
                            raise ValueError("Invalid Quick Review adjustments.")
                        source = work / "input"
                        with source.open("wb") as output:
                            self.receive_media(output, size, export_job)
                        export_preview(source, target, changes, export_job)
                    else:
                        recipe = work / "recipe.json"
                        with recipe.open("wb") as output:
                            self.receive_media(output, size, export_job)
                        current.export_edit(recipe, target, export_job)
                    if export_job.is_set():
                        raise PreparationCancelled()
                    with target.open("rb") as result, suppress(BrokenPipeError, ConnectionResetError, TimeoutError):
                        self.send_response(200)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Content-Disposition", 'attachment; filename="footage-edited.mp4"')
                        self.send_header("Content-Length", str(target.stat().st_size))
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        copyfileobj(result, self.wfile, 1024 * 1024)
            except PreparationCancelled:
                self.reply(409, "Download cancelled.")
            except ValueError as error:
                self.reply(422, str(error))
            except OSError as error:
                if error.errno in (ENOSPC, EDQUOT):
                    self.reply(507, "Temporary storage filled up during export.")
                else:
                    self.reply(500, "Could not complete the download. Try again.")
            finally:
                with state:
                    export_job = None
                    active.release()

        def receive_media(self, output, remaining, stop):
            while remaining:
                if stop.is_set():
                    raise PreparationCancelled()
                block = self.rfile.read(min(remaining, 1024 * 1024))
                if not block:
                    raise ValueError("Upload interrupted. Choose the video and try again.")
                output.write(block)
                remaining -= len(block)

        def do_POST(self):
            nonlocal editor, job, uhd_job, uhd_error, uhd_attempt
            is_face = face is not None and self.path.startswith("/face-swap/")
            is_style = style is not None and self.path.startswith("/style/")
            if not is_face and not is_style and self.path not in ("/upload", "/clear", "/cancel", "/prepare-4k", "/export-preview", "/export-edit"):
                return self.reply(404, "Upload endpoint not found.")
            # Match the actual listener so a different site or a rebound hostname cannot submit footage.
            host = self.loopback_host()
            if self.headers.get("Host") != host or self.headers.get("Origin") != f"http://{host}":
                return self.reply(403, "Open the editor at the loopback URL printed in the terminal.")
            if is_face:
                current = editor
                return face.post(self, current.editable_source if current is not None else None)
            if is_style:
                return style.post(self, editor)
            if self.path in ("/export-preview", "/export-edit"):
                return self.edited_media(self.path == "/export-preview")
            if self.path == "/cancel":
                if self.cancel_preparation():
                    return self.reply(202, "Cancelling preparation…")
                return self.reply(200, "No video is being prepared.")
            if self.path == "/prepare-4k":
                with state:
                    current = editor
                    if current is None or current.prepare_uhd is None:
                        return self.reply(404, "Prepare a video before building 4K playback.")
                    if current.uhd.is_file():
                        return self.reply(200, "4K playback is ready.")
                    if uhd_job is not None:
                        return self.reply(202, "4K playback is already being prepared.", attempt=uhd_attempt)
                    if not active.acquire(blocking=False):
                        return self.reply(409, "Wait for the editor’s current task and try again.")
                    uhd_job = Job()
                    uhd_job.stage = "Building verified 4K playback"
                    uhd_error = None
                    uhd_attempt += 1
                    attempt = uhd_attempt
                # Build in the background; pages follow progress and completion on /events.
                Thread(target=build_uhd, args=(current, uhd_job), daemon=True).start()
                return self.reply(202, "Preparing 4K playback…", attempt=attempt)
            if self.path == "/clear":
                if not active.acquire(blocking=False):
                    with state:
                        if uhd_job is not None:
                            uhd_job.set()
                            return self.reply(409, "Cancelling 4K preparation. Try clearing the video again in a moment.")
                    return self.reply(409, "Wait for preparation to finish before clearing the video.")
                try:
                    if editor is not None:
                        if face is not None:
                            face.discard()
                        if style is not None:
                            style.discard()
                        editor.retired.set()
                        rmtree(directory / "upload")
                        editor = None
                        uhd_error = None
                except OSError:
                    return self.reply(500, "Unable to clear the video. Close the editor and stop its session.")
                finally:
                    active.release()
                return self.reply(200, "Video cleared.")
            value = self.headers.get("Content-Length", "")
            if not re.fullmatch(r"[0-9]{1,18}", value) or int(value) == 0:
                return self.reply(400, "Choose a nonempty video file.")
            if self.headers.get("Content-Type") != "application/octet-stream":
                return self.reply(415, "Choose a video file in the upload form.")
            with state:
                if not active.acquire(blocking=False):
                    return self.reply(409, "A video is already being prepared.")
                job = UploadPreparation()
            try:
                if editor is not None:
                    return self.reply(409, "This session already has a video. Reload to open the editor.")
                remaining = int(value)
                if remaining >= disk_usage(directory).free:
                    return self.reply(413, "The file is too large for available temporary memory.")
                # Only publish routes after a complete build. A failed attempt leaves a clean workspace for retry.
                working = directory / "upload"
                working.mkdir()
                try:
                    source = working / "input.mp4"
                    with source.open("wb") as output:
                        self.receive_media(output, remaining, job)
                    ready = build(source, working, job)
                    with state:
                        if job.is_set():
                            raise PreparationCancelled()
                        editor = ready
                        job = None
                finally:
                    if editor is None:
                        rmtree(working)
                self.reply(200, "Ready")
            except PreparationCancelled:
                self.reply(409, "Preparation cancelled. You can choose another video.")
            except PreviewOnly as error:
                self.reply(422, str(error), preview=True)
            except ValueError as error:
                self.reply(422, str(error))
            except TimeoutError:
                self.reply(408, "Upload timed out. Try again.")
            except ImportError:
                self.reply(500, "A video-processing dependency could not load. Restart the editor using its Python environment.")
            except OSError as error:
                if error.errno in (ENOSPC, EDQUOT):
                    self.reply(507, "Temporary storage filled up during preparation. Close unused editor sessions to free space and try again.")
                elif error.errno in (ENOMEM, EAGAIN):
                    self.reply(503, "The system could not start a video-processing task. Close unused apps and try again.")
                else:
                    self.reply(500, "Preparation could not access its temporary files or start a processing task. Restart the editor and try again.")
            finally:
                with state:
                    job = None
                    active.release()

    def build_uhd(current, task):
        nonlocal uhd_job, uhd_error
        message = None
        try:
            current.prepare_uhd(task)
            if task.is_set():
                message = "4K preparation was cancelled."
        except ValueError as error:
            message = str(error)
        except OSError as error:
            message = ("Temporary storage filled up. Close unused editor sessions and retry 4K."
                       if error.errno in (ENOSPC, EDQUOT) else "Could not create temporary files for 4K playback.")
        except Exception:
            message = "Could not build 4K playback. See the launch terminal for details."
        finally:
            with state:
                uhd_job = None
                uhd_error = message
                active.release()

    return Upload


def file_handler(files, source_extension="mp4"):
    revoked = Event()

    class Review(BaseHTTPRequestHandler):
        retired = revoked

        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def respond(self, body):
            route = urlsplit(self.path).path
            target = files.get(route)
            if revoked.is_set() or target is None or not target.is_file():
                self.send_error(404)
                return
            try:
                size=target.stat().st_size
            except FileNotFoundError:
                self.send_error(404)
                return
            interval=self.headers.get("Range")
            first,last=0,size-1
            if interval:
                match=re.fullmatch(r"bytes=(\d+)-(\d*)",interval)
                if match:
                    first=int(match[1])
                    last=min(last,int(match[2])) if match[2] else last
                if not match or first>last:
                    self.send_response(416)
                    self.send_header("Content-Range",f"bytes */{size}")
                    self.end_headers()
                    return
            self.send_response(206 if interval else 200)
            original = route == "/source.mp4"
            content_type = mimetypes.guess_type("footage." + source_extension if original else target)[0] or "application/octet-stream"
            self.send_header("Content-Type", "text/javascript" if target.suffix==".mjs" else content_type)
            if original:
                self.send_header("Content-Disposition", f'attachment; filename="source-quality.{source_extension}"')
            self.send_header("Accept-Ranges","bytes")
            self.send_header("Permissions-Policy","gamepad=(self)")
            self.send_header("Cache-Control","no-store")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(last-first+1))
            if interval:
                self.send_header("Content-Range",f"bytes {first}-{last}/{size}")
            self.end_headers()
            if body:
                with suppress(FileNotFoundError, BrokenPipeError, ConnectionResetError), target.open("rb") as f:
                    f.seek(first)
                    remaining=last-first+1
                    while remaining and not revoked.is_set() and (block:=f.read(min(remaining,65536))):
                        self.wfile.write(block)
                        remaining-=len(block)
    return Review


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("assets",type=Path)
    parser.add_argument("--video",type=Path,help="MP4 matching the supplied timeline")
    parser.add_argument("--source",type=Path,help="Untouched input MP4 to serve at /source.mp4")
    parser.add_argument("--uhd",type=Path,help="4K MP4 on the same timeline")
    parser.add_argument("--regions",type=Path,help="Python-generated augmentation regions")
    parser.add_argument("--skin",type=Path,help="Directory of Python-generated skin mask pages")
    parser.add_argument("--cleanup-tracks",type=Path,help="Joint-relative cleanup track sidecar")
    parser.add_argument("--motion-study",type=Path,help="Recorded secondary motion measurements")
    parser.add_argument("--motion-splats",type=Path,help="Recorded temporal Gaussian tracks")
    parser.add_argument("--port",type=int,default=0)
    args=parser.parse_args()
    for media in (args.video,args.source,args.uhd,args.regions,args.cleanup_tracks,args.motion_study,args.motion_splats):
        if media is not None and not media.is_file():
            parser.error(f"File not found: {media}")
    with ThreadingHTTPServer(("127.0.0.1",args.port),handler(args.assets,args.video,args.source,args.uhd,args.regions,args.skin,args.cleanup_tracks,args.motion_study,args.motion_splats)) as server:
        print(f"http://127.0.0.1:{server.server_port}/",flush=True)
        server.serve_forever()
