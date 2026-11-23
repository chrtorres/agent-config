"""Routes for learning recording styles and rendering the editor's video in one.

Learned styles are the one thing the editor keeps between sessions: each is a
small JSON profile of aggregate measurements (no pixels, faces or sound) in a
private library directory. Everything else, including rendered results, stays
in the volatile session and is removed with it.
"""
from contextlib import suppress
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import secrets
from shutil import rmtree
import signal
import subprocess
import sys
from tempfile import TemporaryFile
from threading import Event, Lock, Thread
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from tools.progress import Estimate, read_progress
from tools.recording_style import MATCH_THRESHOLD, describe, similarity, valid_profile

APP = Path(__file__).resolve().parent.parent
STYLE_ID = re.compile(r"[0-9a-f]{16}")


def clean_name(value, fallback):
    """A display name without control characters, at most 60 characters."""
    name = re.sub(r"[\x00-\x1f\x7f]+", " ", value or "").strip()[:60]
    return name or fallback


class Library:
    """Learned styles on disk, one owner-only JSON file per style."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.lock = Lock()

    def entries(self):
        result = []
        if not self.directory.is_dir():
            return result
        for path in sorted(self.directory.glob("*.json")):
            if not STYLE_ID.fullmatch(path.stem):
                continue
            try:
                entry = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(entry, dict) and valid_profile(entry.get("profile")) and isinstance(entry.get("name"), str):
                result.append({**entry, "id": path.stem})
        result.sort(key=lambda entry: entry.get("created", ""))
        return result

    def listing(self):
        return [{"id": entry["id"], "name": entry["name"], "created": entry.get("created"),
                 "summary": entry["profile"].get("summary") or describe(entry["profile"])} for entry in self.entries()]

    def get(self, style_id):
        if not STYLE_ID.fullmatch(style_id or ""):
            return None
        return next((entry for entry in self.entries() if entry["id"] == style_id), None)

    def export(self):
        with self.lock:
            entries = self.entries()
        if not entries:
            return None
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for entry in entries:
                # Preserve library filenames so the extracted files work with --styles.
                filename = entry.pop("id") + ".json"
                archive.writestr(filename, json.dumps(entry, ensure_ascii=False))
        return buffer.getvalue()

    def closest(self, profile):
        """(entry, percent) of the most similar stored style, or (None, 0)."""
        best, score = None, 0.
        for entry in self.entries():
            match, _ = similarity(profile, entry["profile"])
            if match > score:
                best, score = entry, match
        return best, score

    def learn(self, profile, name=None):
        """Store a new style unless one already matches at or above the threshold.

        Returns {"kind": "duplicate", ...} or {"kind": "added", ...}.
        """
        with self.lock:
            entry, match = self.closest(profile)
            if entry is not None and match >= MATCH_THRESHOLD:
                _, groups = similarity(profile, entry["profile"])
                return {"kind": "duplicate", "id": entry["id"], "name": entry["name"], "match": match, "groups": groups}
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            style_id = secrets.token_hex(8)
            count = len(self.entries())+1
            record = {"name": clean_name(name, f"Style {count}"), "profile": profile,
                      "created": datetime.now(timezone.utc).isoformat(timespec="microseconds")}
            path = self.directory/f"{style_id}.json"
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as output:
                json.dump(record, output)
            return {"kind": "added", "id": style_id, "name": record["name"], "summary": profile.get("summary"),
                    "closest": None if entry is None else {"name": entry["name"], "match": match}}

    def delete(self, style_id):
        with self.lock:
            if not STYLE_ID.fullmatch(style_id or ""):
                return False
            path = self.directory/f"{style_id}.json"
            if not path.is_file():
                return False
            path.unlink()
            return True


class StyleRoutes:
    def __init__(self, session, library, style_model, file_handler):
        self.directory = session/"style"
        self.library = Library(library)
        self.style_model = style_model
        self.file_handler = file_handler
        self.lock = Lock()
        self.job = None
        self.kind = None
        self.estimate = None
        self.outcome = None
        self.report = None
        self.result = None

    # ---------------------------------------------------------------- state

    def status(self):
        with self.lock:
            phase = "idle"
            if self.job is not None:
                phase = "cancelling" if self.job.is_set() else self.kind
            state = {"phase": phase, "outcome": self.outcome, "report": self.report,
                     "library": self.library.listing(), "threshold": MATCH_THRESHOLD}
            if self.job is not None:
                fraction, label = read_progress(self.directory/"progress")
                if label:
                    state["progress"] = label
                if self.estimate is not None:
                    state.update(self.estimate.snapshot(fraction))
        return state

    def cancel(self):
        with self.lock:
            if self.job is not None:
                self.job.set()
                return True
        return False

    def discard(self):
        """Drop the session's rendered result (the library is kept)."""
        self.cancel()
        with self.lock:
            if self.job is not None:
                return False
            if self.result is not None:
                self.result.retired.set()
            rmtree(self.directory, ignore_errors=True)
            self.result = self.report = None
            return True

    # ---------------------------------------------------------------- routes

    def get(self, request, body):
        path = urlsplit(request.path).path
        if path == "/style/status" and body:
            return request.reply(200, json.dumps(self.status()))
        if path == "/style/styles.zip":
            archive = self.library.export()
            if archive is None:
                return request.send_error(404, "No saved styles to export.")
            request.send_response(200)
            request.send_header("Content-Type", "application/zip")
            request.send_header("Content-Disposition", 'attachment; filename="footage-styles.zip"')
            request.send_header("Cache-Control", "no-store")
            request.send_header("Content-Length", str(len(archive)))
            request.end_headers()
            if body:
                request.wfile.write(archive)
            return
        if path == "/style/result.mp4":
            with self.lock:
                result = self.result
            if result is not None:
                return result.respond(request, body)
        request.send_error(404)

    def post(self, request, editor):
        path = urlsplit(request.path).path
        if path == "/style/cancel":
            active = self.cancel()
            return request.reply(202 if active else 200, "Cancelling." if active else "Nothing is running.")
        if path == "/style/clear":
            if not self.discard():
                return request.reply(409, "Wait for the current style task to stop.")
            return request.reply(200, "Result cleared.")
        if path == "/style/delete":
            with self.lock:
                if self.job is not None:
                    return request.reply(409, "Wait for the current style task to finish.")
            if not self.library.delete(request.headers.get("X-Style-Id")):
                return request.reply(404, "That style is not in the library.")
            return request.reply(200, "Style deleted.")
        if path not in ("/style/learn", "/style/apply"):
            return request.reply(404, "Unknown style action.")
        if editor is None:
            return request.reply(409, "Open a video in the editor first.")
        if path == "/style/apply":
            entry = self.library.get(request.headers.get("X-Style-Id"))
            if entry is None:
                return request.reply(404, "That style is not in the library.")
        with self.lock:
            if self.job is not None:
                return request.reply(409, "A style task is already running.")
            if path == "/style/apply" and self.result is not None:
                self.result.retired.set()
                self.result = None
            rmtree(self.directory, ignore_errors=True)
            self.directory.mkdir(mode=0o700)
            self.job, self.estimate, self.outcome = Event(), Estimate(), None
            self.kind = "learning" if path == "/style/learn" else "rendering"
            if path == "/style/apply":
                self.report = None
            job = self.job
        if path == "/style/learn":
            name = unquote(request.headers.get("X-Style-Name", ""))
            Thread(target=self.learn, args=(editor, name, job), daemon=True).start()
            return request.reply(202, "Learning the recording style…")
        Thread(target=self.apply, args=(editor, entry, job), daemon=True).start()
        return request.reply(202, "Rendering in “" + entry["name"] + "”…")

    # ---------------------------------------------------------------- jobs

    def run(self, arguments, job):
        """Run the style tool in its own process group so a cancel stops it at once."""
        environment = dict(os.environ, FOOTAGE_PROGRESS=str(self.directory/"progress"))
        command = [sys.executable, "-B", str(APP/"tools/recording_style.py"), *map(str, arguments),
                   "--style-model", str(self.style_model())]
        with TemporaryFile(dir=self.directory) as errors, subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors,
                env=environment, start_new_session=True) as process:
            while True:
                try:
                    code = process.wait(timeout=.5)
                    break
                except subprocess.TimeoutExpired:
                    if job.is_set():
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise InterruptedError()
            if code:
                errors.seek(max(0, errors.seek(0, os.SEEK_END)-2048))
                lines = errors.read().decode(errors="replace").strip().splitlines()
                detail = lines[-1] if lines and "Traceback" not in lines[-1] and "/" not in lines[-1] else ""
                raise ValueError(detail or "The style tool could not process this video.")

    def finish(self, job, outcome):
        with self.lock:
            if self.job is job:
                self.job = None
                self.outcome = outcome

    def learn(self, editor, name, job):
        outcome = None
        try:
            profile_path = self.directory/"profile.json"
            self.run(["learn", editor.editable_source, profile_path, "--encoding-from", editor.original_source], job)
            profile = json.loads(profile_path.read_text())
            if not valid_profile(profile):
                raise ValueError("The measured style was incomplete.")
            outcome = self.library.learn(profile, name)
        except InterruptedError:
            outcome = {"kind": "cancelled"}
        except (OSError, ValueError) as error:
            outcome = {"kind": "error", "message": str(error) if isinstance(error, ValueError) else
                       "Could not use temporary storage for style learning."}
        finally:
            with suppress(OSError):
                (self.directory/"profile.json").unlink()
            self.finish(job, outcome)

    def apply(self, editor, entry, job):
        outcome = None
        try:
            profile_path = self.directory/"style.json"
            profile_path.write_text(json.dumps(entry["profile"]))
            output, report = self.directory/"styled.mp4", self.directory/"report.json"
            self.run(["apply", editor.editable_source, profile_path, output, "--report", report], job)
            result = json.loads(report.read_text())
            result.update(style=entry["name"], style_id=entry["id"])
            with self.lock:
                self.report = result
                self.result = self.file_handler({"/style/result.mp4": output})
            outcome = {"kind": "rendered", "name": entry["name"], "match": result["match"]}
        except InterruptedError:
            outcome = {"kind": "cancelled"}
        except (OSError, ValueError, KeyError) as error:
            outcome = {"kind": "error", "message": str(error) if isinstance(error, ValueError) else
                       "Could not render the styled video in temporary storage."}
        finally:
            self.finish(job, outcome)
