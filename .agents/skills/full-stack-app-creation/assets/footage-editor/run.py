"""Start a local editing session from an MP4 supplied on stdin."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from getpass import getpass
import hashlib
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen

sys.dont_write_bytecode = True
from app.serve import handler

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


@contextmanager
def session_directory():
    ram = Path("/dev/shm")
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    if not any(row.split(" - ", 1)[0].split()[4] == str(ram) and
               row.split(" - ", 1)[1].split()[0] == "tmpfs" for row in mounts):
        raise ValueError("A Linux tmpfs at /dev/shm is required")
    with TemporaryDirectory(prefix="footage-editor-", dir=ram) as directory:
        yield Path(directory)


def model_files(directory, offline):
    directory.mkdir()
    print("Verifying public inference models", flush=True)
    for name, (relative, expected) in MODELS.items():
        try:
            if offline:
                data = (offline / name).read_bytes()
            else:
                for attempt in range(3):
                    try:
                        with urlopen(MODEL_ORIGIN + relative, timeout=30) as response:
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
        (directory / name).write_bytes(data)


def validate_input(source):
    import av
    with av.open(str(source)) as container:
        if len(container.streams.video) != 1 or len(container.streams.audio) != 1:
            raise ValueError("Supply an MP4 with one H.264 video stream and one AAC audio stream")
        video, audio = container.streams.video[0], container.streams.audio[0]
        if (video.codec_context.name != "h264" or audio.codec_context.name != "aac" or
                video.width * 16 != video.height * 9 or video.width % 2 or video.height % 2):
            raise ValueError("Supply an even-sized 9:16 portrait H.264/AAC MP4")


def prepare(source, directory, offline):
    models = directory / "models"
    model_files(models, offline)
    data = directory / "data"
    timeline = data / "timeline" / "timeline.json"
    regions = data / "regions.json"
    skin = data / "skin"
    cleanup = data / "cleanup-tracks.json"
    world = data / "world.json"
    analysis = data / "motion-study.json"
    splats = data / "motion-splats.json"
    cancelled = Event()
    worker_environment = {**os.environ, "TMPDIR": str(directory),
                          "XDG_CACHE_HOME": str(directory / "cache"),
                          "MPLCONFIGDIR": str(directory / "matplotlib")}
    worker_environment.pop("FFREPORT", None)

    def step(label, module, *args):
        if cancelled.is_set():
            return
        print(label, flush=True)
        with subprocess.Popen(
            [sys.executable, "-B", APP / "tools" / (module + ".py"), *args],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=worker_environment, start_new_session=True,
        ) as process:
            while True:
                try:
                    code = process.wait(timeout=.5)
                    break
                except subprocess.TimeoutExpired:
                    if cancelled.is_set():
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        return
            if code:
                raise ValueError(label + " failed. Check the input format, tracking coverage and available RAM.")

    with ThreadPoolExecutor(max_workers=3) as pool:
        try:
            media = pool.submit(step, "Building playback media", "media", "build", source, data)
            pose = pool.submit(step, "Tracking pose and foreground", "prepare", source, models / "pose.task", data)
            depth = pool.submit(step, "Estimating pose depth", "measure_motion", "world", source, models / "pose.task", world)
            pose.result()
            face = pool.submit(step, "Tracking visible features", "augment", source, models / "face.task", timeline, regions,
                               "--hand-model", models / "hand.task")
            tone = pool.submit(step, "Estimating skin masks", "skin", source, models / "skin.tflite", timeline, skin)
            face.result()
            stabilize = pool.submit(step, "Preparing edit cleanup", "cleanup_tracks", regions, timeline, cleanup)
            dynamics = pool.submit(step, "Measuring recorded motion", "measure_motion", "measure", source, timeline, regions, analysis)
            depth.result()
            preview = pool.submit(step, "Preparing motion preview", "build_splats", source, timeline, splats, "--world", world)
            for stage in (media, tone, stabilize, dynamics, preview):
                stage.result()
            step("Verifying timing and audio", "media", "verify", source, data)
        finally:
            cancelled.set()
    return data, regions, skin, cleanup, analysis, splats


def stop(*_):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, help="Use an offline directory of verified public model files")
    parser.add_argument("--check", action="store_true", help="Build and verify the session, then release its working data")
    args = parser.parse_args()
    entered = getpass("Input video path: ") if sys.stdin.isatty() else sys.stdin.readline().rstrip("\r\n")
    if not entered:
        parser.exit(2, "Supply an input video path on stdin.\n")
    signal.signal(signal.SIGTERM, stop)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        with session_directory() as session:
            # Workers receive only a neutral name in the volatile workspace.
            alias = session / "input.mp4"
            alias.symlink_to(Path(entered).expanduser().resolve(strict=True))
            validate_input(alias)
            data, regions, skin, cleanup, analysis, splats = prepare(alias, session, args.models)
            if args.check:
                print("Clean rebuild and media verification passed.")
                return
            with ThreadingHTTPServer(("127.0.0.1", 0), handler(
                data, data / "native.mp4", alias, data / "4k.mp4", regions, skin, cleanup, analysis, splats
            )) as server:
                print(f"http://127.0.0.1:{server.server_port}/", flush=True)
                server.serve_forever()
    except KeyboardInterrupt:
        return
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except (OSError, ImportError):
        parser.exit(1, "Unable to read input or initialize the engine. Check the setup and input file.\n")


if __name__ == "__main__":
    main()
