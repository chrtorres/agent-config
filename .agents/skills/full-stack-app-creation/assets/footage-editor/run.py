"""Start a local editing session from a browser upload or an MP4 path on stdin."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from getpass import getpass
import hashlib
from http.server import ThreadingHTTPServer
from importlib.util import find_spec
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile
from threading import Event
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen

sys.dont_write_bytecode = True
from app.serve import PreparationCancelled, PreviewOnly, handler, upload_handler

APP = Path(__file__).resolve().parent
MODEL_ORIGIN = "https://storage.googleapis.com/mediapipe-models/"
MODELS = {
    "pose.task": ("pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
                  "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"),
    "face.task": ("face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                  "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
    "hand.task": ("hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
                  "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"),
    "skin.tflite": ("image_segmenter/selfie_multiclass_256x256/float32/1/selfie_multiclass_256x256.tflite",
                    "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0"),
}


# Pretrained SqueezeNet 1.1 (ONNX model zoo) for the deep look statistics of recording styles.
STYLE_MODELS = {
    "style.onnx": ("https://github.com/onnx/models/raw/main/validated/vision/classification/squeezenet/model/"
                   "squeezenet1.1-7.onnx", "1eeff551a67ae8d565ca33b572fc4b66e3ef357b0eb2863bb9ff47a918cc4088"),
}


def ensure_runtime(parser):
    required = ("av", "cv2", "imageio_ffmpeg", "mediapipe", "numpy", "PIL", "scipy")
    missing = [name for name in required if find_spec(name) is None]
    if not missing:
        try:
            import av
            import imageio_ffmpeg

            imageio_ffmpeg.get_ffmpeg_exe()
            return
        except (ImportError, OSError, RuntimeError):
            missing = ["PyAV or FFmpeg runtime"]
    environment = APP / ".venv"
    interpreter = environment / "bin" / "python"
    if interpreter.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        try:
            os.execv(interpreter, [str(interpreter), "-B", str(APP / "run.py"), *sys.argv[1:]])
        except OSError:
            parser.exit(1, "Unable to launch the editor's .venv. Recreate it using the README setup steps.\n")
    parser.exit(1, "Footage Editor needs a working Python environment (" + ", ".join(missing) +
                "). Install requirements.txt in a .venv and run .venv/bin/python -B run.py.\n")


@contextmanager
def session_directory():
    ram = Path("/dev/shm")
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    if not any(row.split(" - ", 1)[0].split()[4] == str(ram) and
               row.split(" - ", 1)[1].split()[0] == "tmpfs" for row in mounts):
        raise ValueError("A Linux tmpfs at /dev/shm is required")
    with TemporaryDirectory(prefix="footage-editor-", dir=ram) as directory:
        yield Path(directory)


def model_files(directory, offline, names=None, catalog=None):
    catalog = MODELS if catalog is None else catalog
    directory.mkdir(exist_ok=True)
    print("Verifying public inference models", flush=True)
    def verify_model(item):
        name, (relative, expected) = item
        destination = directory / name
        if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == expected:
            return
        try:
            if offline:
                data = (offline / name).read_bytes()
            else:
                for attempt in range(3):
                    try:
                        url = relative if relative.startswith("https://") else MODEL_ORIGIN + relative
                        with urlopen(url, timeout=30) as response:
                            data = response.read(24 * 1024 * 1024 + 1)
                        break
                    except (URLError, TimeoutError):
                        if attempt == 2:
                            raise
                        sleep(2 ** attempt)
        except OSError:
            raise ValueError("Unable to obtain the verified public model " + name) from None
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Model verification failed for " + name)
        with TemporaryDirectory(dir=directory) as staging:
            pending = Path(staging) / name
            pending.write_bytes(data)
            pending.replace(destination)

    items = [(name, catalog[name]) for name in names] if names is not None else list(catalog.items())
    if offline:
        for item in items:
            verify_model(item)
    else:
        with ThreadPoolExecutor(max_workers=len(items)) as pool:
            list(pool.map(verify_model, items))


def validate_input(source):
    """Accept only MP4 files the browser plays directly. Other formats are rejected, not converted."""
    from tools.media import require_mp4
    return "normalize" if require_mp4(source) else None


def preparation_step(directory, is_stopping, label, module, *args, progress=None):
    worker_environment = {**os.environ, "TMPDIR": str(directory),
                          "XDG_CACHE_HOME": str(directory / "cache"),
                          "MPLCONFIGDIR": str(directory / "matplotlib")}
    worker_environment.pop("FFREPORT", None)
    worker_environment.pop("FOOTAGE_PROGRESS", None)
    if progress is not None:
        worker_environment["FOOTAGE_PROGRESS"] = str(progress)

    if is_stopping():
        return
    print(label, flush=True)
    with TemporaryFile(dir=directory) as diagnostics, subprocess.Popen(
        [sys.executable, "-B", APP / "tools" / (module + ".py"), *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=diagnostics,
        env=worker_environment, start_new_session=True,
    ) as process:
        while True:
            try:
                code = process.wait(timeout=.5)
                break
            except subprocess.TimeoutExpired:
                if is_stopping():
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    return
        if code:
            if module == "prepare" and code == 3:
                raise PreviewOnly("This video is open in Quick Review. The performer wasn’t visible consistently enough for motion tools.")
            end = diagnostics.seek(0, os.SEEK_END)
            diagnostics.seek(max(0, end - 8192))
            detail = diagnostics.read().decode("utf-8", errors="replace").strip()
            detail = detail.replace(str(directory), "<session>").replace(str(Path.home()), "~")
            print(f"{label} failed (exit status {code})", file=sys.stderr, flush=True)
            if detail:
                print(detail, file=sys.stderr, flush=True)
            if "No space left on device" in detail:
                raise ValueError(f"{label} ran out of temporary storage. Close unused sessions and try again.")
            if module == "media" and "Media validation failed:" in detail:
                checks = detail.rsplit("Media validation failed:", 1)[1].splitlines()[0].strip()
                allowed = ("native_file_exact", "4k_dimensions", "presentation_timestamps_exact",
                           "video_duration_exact", "audio_packets_and_timing_exact",
                           "decoded_audio_samples_and_timing_exact")
                failed = [name for name in checks.split(", ") if name in allowed]
                if failed:
                    raise ValueError(f"{label} could not preserve " + ", ".join(
                        name.replace("_exact", "").replace("_", " ") for name in failed) + ".")
            raise ValueError(f"{label} failed. See the launch terminal for details.")


# Relative work per step, measured on a 1080p clip after the parallel skin and flow changes.
# The steps overlap, so the weighted sum tracks total work rather than elapsed time.
STEP_WEIGHTS = {"models": .5, "normalize": 4, "pose": 5.3, "face": 5.7, "tone": 7, "preview": 5.1,
                "cleanup": .3, "dynamics": 8.3}


def prepare(source, directory, offline, conversion=None, cancel=None):
    from tools.progress import Tracker
    models = directory.parent / "models"
    weights = {name: weight for name, weight in STEP_WEIGHTS.items() if name != "normalize" or conversion}
    tracker = Tracker(directory / "progress", weights)
    if cancel is not None:
        cancel.stage = "Checking processing models"
        cancel.tracker = tracker
    model_files(models, offline)
    tracker.finish("models")
    data = directory / "data"
    timeline = data / "timeline" / "timeline.json"
    regions = data / "regions.json"
    skin = data / "skin"
    cleanup = data / "cleanup-tracks.json"
    world = data / "world.json"
    analysis = data / "motion-study.json"
    splats = data / "motion-splats.json"
    stopped = Event()

    def is_stopping():
        return stopped.is_set() or (cancel is not None and cancel.is_set())

    def step(name, label, module, *args):
        if cancel is not None and not is_stopping():
            cancel.stage = label
        preparation_step(directory, is_stopping, label, module, *args, progress=tracker.path(name))
        tracker.finish(name)

    if conversion:
        # Tracking and browser playback must see the same upright, square-pixel raster.
        native_source = directory / "upright.mp4"
        step("normalize", "Preparing video orientation", "media", "normalize", source, native_source)
        source = native_source

    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {}

        def submit(name, label, module, *args):
            pending[pool.submit(step, name, label, module, *args)] = name

        try:
            submit("pose", "Tracking pose, depth and foreground", "prepare", source, models / "pose.task",
                   data, "--world", world)
            # Surface a failed worker even when another branch is still tracking thousands of frames.
            while pending:
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for task in completed:
                    task.result()
                for task in completed:
                    name = pending.pop(task)
                    if name == "pose":
                        submit("face", "Tracking visible features", "augment", source, models / "face.task",
                               timeline, regions, "--hand-model", models / "hand.task")
                        submit("tone", "Estimating skin masks", "skin", source, models / "skin.tflite", timeline, skin)
                        submit("preview", "Preparing motion preview", "build_splats", source, timeline, splats,
                               "--world", world)
                    elif name == "face":
                        submit("cleanup", "Preparing edit cleanup", "cleanup_tracks", regions, timeline, cleanup)
                        submit("dynamics", "Measuring recorded motion", "measure_motion", "measure",
                               source, timeline, regions, analysis)
        finally:
            stopped.set()
    if cancel is not None and cancel.is_set():
        raise PreparationCancelled()
    return source, data, regions, skin, cleanup, analysis, splats


def stop(*_):
    raise KeyboardInterrupt


class SessionServer(ThreadingHTTPServer):
    # Finish active requests before the outer context removes their volatile files.
    daemon_threads = False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, help="Use an offline directory of verified public model files")
    parser.add_argument("--check", action="store_true", help="Build and verify the session, then release its working data")
    parser.add_argument("--face-models", type=Path, default=Path.home() / ".cache/footage-editor/face-models",
                        help="Verified Face Swap model directory")
    parser.add_argument("--port", type=int, default=0, help="Listen on a specific loopback port")
    parser.add_argument("--styles", type=Path,
                        default=Path(os.environ.get("XDG_DATA_HOME") or Path.home()/".local/share")/"footage-editor/styles",
                        help="Private directory for learned recording styles (kept between sessions)")
    args = parser.parse_args()
    ensure_runtime(parser)
    if sys.stdin.isatty():
        entered = getpass("Input video path: ") if args.check else ""
    else:
        entered = sys.stdin.readline().rstrip("\r\n")
    if args.check and not entered:
        parser.error("--check requires an input video path on stdin")
    signal.signal(signal.SIGTERM, stop)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        with session_directory() as session:
            def tracked_step(stop, directory, label, module, *args):
                from tools.progress import Tracker
                # Expose one worker's progress file to the status stream through the job.
                tracker = Tracker(directory / "progress", {"work": 1})
                stop.tracker = tracker
                preparation_step(directory, stop.is_set, label, module, *args, progress=tracker.path("work"))
                tracker.finish("work")

            def build(source, working, cancel=None):
                conversion = validate_input(source)
                native, data, regions, skin, cleanup, analysis, splats = prepare(
                    source, working, args.models, conversion, cancel)

                def build_uhd(stop):
                    with TemporaryDirectory(dir=working) as scratch:
                        tracked_step(stop, Path(scratch), "Building verified 4K playback", "media",
                                     "upscale-verified", native, scratch)
                        if not stop.is_set():
                            (Path(scratch) / "4k.mp4").replace(data / "4k.mp4")

                def export_edit(recipe, output, stop):
                    tracked_step(stop, output.parent, "Rendering shape and color edits", "export_edit",
                                 native, data / "timeline" / "timeline.json", regions, skin, output,
                                 "--settings", recipe, "--cleanup-tracks", cleanup, "--motion-study", analysis)

                return handler(data, native, source, data / "4k.mp4",
                               regions, skin, cleanup, analysis, splats, prepare_uhd=build_uhd,
                               export_edit=export_edit)

            def export_preview(source, output, adjustments, stop):
                validate_input(source)
                tracked_step(stop, output.parent, "Rendering Quick Review edits", "media",
                             "grade", source, output, "--adjustments", *map(str, adjustments))

            def run_face_tool(command, working, cancel):
                with TemporaryFile(dir=working) as errors, subprocess.Popen(
                    command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors,
                    start_new_session=True,
                ) as process:
                    while True:
                        try:
                            code = process.wait(timeout=.5)
                            break
                        except subprocess.TimeoutExpired:
                            if cancel is not None and cancel.is_set():
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                                return
                    if code:
                        errors.seek(max(0, errors.seek(0, os.SEEK_END)-4096))
                        detail = errors.read().decode(errors="replace").strip().splitlines()
                        if detail and not any(part in detail[-1] for part in ("/", "Traceback")):
                            raise ValueError(detail[-1])
                        raise ValueError("Face Swap failed during processing or verification.")

            def face_mesh_model():
                cache = session / "models"
                model_files(cache, args.models, ("face.task",))
                return cache / "face.task"

            def build_swap(source, target, working, source_index, target_index, cancel, selection=None, image=False):
                command = [sys.executable, "-B", APP / "tools/face_swap_video.py", source, target, working,
                           args.face_models, "--source-index", str(source_index), "--target-index", str(target_index),
                           "--image" if image else "--preview", "--mesh-model", face_mesh_model()]
                if selection is not None:
                    command.extend(["--target-point", *map(str, selection)])
                run_face_tool(command, working, cancel)

            def build_mask(frame, overlay, x, y, curvature=False):
                command = [sys.executable, "-B", APP / "tools/face_target_mask.py",
                           frame, overlay, args.face_models, str(x), str(y)]
                if curvature:
                    command.extend(["--curvature-model", face_mesh_model()])
                run_face_tool(command, frame.parent, None)

            if entered:
                # Workers receive only a neutral name in the volatile workspace.
                working = session / "upload"
                working.mkdir()
                alias = working / "input.mp4"
                alias.symlink_to(Path(entered).expanduser().resolve(strict=True))
                review = build(alias, working)
                if args.check:
                    review.prepare_uhd(Event())
                    print("Clean rebuild and media verification passed.")
                    return
            else:
                review = None
            def style_model():
                cache = session / "models"
                model_files(cache, args.models, ("style.onnx",), STYLE_MODELS)
                return cache / "style.onnx"

            review_handler = upload_handler(session, build, review, build_swap, build_mask, export_preview,
                                            {"library": args.styles, "model": style_model})
            with SessionServer(("127.0.0.1", args.port), review_handler) as server:
                print(f"http://127.0.0.1:{server.server_port}/", flush=True)
                try:
                    server.serve_forever()
                finally:
                    review_handler.stop_jobs()
    except KeyboardInterrupt:
        return
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except (OSError, ImportError):
        parser.exit(1, "Unable to read input or initialize the engine. Check the setup and input file.\n")


if __name__ == "__main__":
    main()
