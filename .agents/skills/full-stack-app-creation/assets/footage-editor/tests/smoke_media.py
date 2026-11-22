"""Run the format matrix, including a one-time 4K encoder failure, in volatile storage."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import av
import imageio_ffmpeg
import numpy as np
from PIL import Image

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from tools.media import inspect


def verify_downloads(fixtures):
    base = fixtures / "mp4.mp4"
    changed = fixtures / "output-prepared-mp4.mp4"
    assert inspect(base)[1:] == inspect(changed)[1:], "Edited MP4 must preserve frame timing and AAC"
    with av.open(str(base)) as source, av.open(str(changed)) as output:
        before = next(source.decode(video=0)).to_ndarray(format="rgb24")
        after = next(output.decode(video=0)).to_ndarray(format="rgb24")
        assert np.any(before != after), "Color edit must change decoded pixels"
    for original, output in (("rotated.mp4", "output-prepared-rotated.mp4"), ("silent.mp4", "output-quick.mp4")):
        with av.open(str(fixtures / original)) as source:
            before = [frame.pts * frame.time_base for frame in source.decode(video=0)]
        after = inspect(fixtures / output)[2]
        assert len(after) == len(before), f"{output} has {len(after)} frames for {len(before)} input pictures"
        origin = before[0] - after[0]
        assert all(abs(a-b-origin) <= .001 for a, b in zip(before, after)), f"{output} changed frame timing"
    for name in ("mp4.mp4", "rotated.mp4"):
        # The rotated fixture is prepared upright, so its frame download swaps width and height.
        expected = inspect(base)[0] if name == "mp4.mp4" else inspect(base)[0][::-1]
        with Image.open(fixtures / f"output-frame-{name}.png") as frame:
            assert list(frame.size) == expected
    for extension in ("jpg", "png", "webp"):
        with Image.open(fixtures / f"output-still.{extension}.png") as edited, \
                Image.open(fixtures / f"still.{extension}") as original:
            assert edited.size == original.size
            assert edited.convert("RGB").getpixel((5, 5)) != original.convert("RGB").getpixel((5, 5))
    print("Verified downloaded pictures, changed pixels, frame count, video timing and AAC.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--playwright", required=True, type=Path)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--models", type=Path, help="Optional directory of verified public MediaPipe models")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="footage-media-smoke-", dir="/dev/shm") as directory:
        root = Path(directory)
        fixtures = root / "fixtures"
        shutil.copytree(args.fixtures, fixtures, ignore=shutil.ignore_patterns("output-*"))

        marker = shlex.quote(str(root / "failed-once"))
        encoder = shlex.quote(imageio_ffmpeg.get_ffmpeg_exe())
        wrapper = root / "ffmpeg-test"
        wrapper.write_text(f"""#!/bin/sh
case "$*" in
  *unsharp=*) if [ ! -e {marker} ]; then
    touch {marker}
    echo "Injected 4K encoder failure" >&2
    exit 1
  fi;;
esac
exec {encoder} "$@"
""")
        wrapper.chmod(0o700)
        env = dict(os.environ, IMAGEIO_FFMPEG_EXE=str(wrapper), FOOTAGE_EXPECT_UHD_FAILURE="1", TMPDIR=directory)
        command = [sys.executable, "-B", "run.py"]
        if args.models:
            command.extend(["--models", str(args.models.resolve())])
        with (root / "errors").open("w+") as errors, subprocess.Popen(
                command, cwd=APP, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=errors, env=env, text=True) as server:
            try:
                url = server.stdout.readline().strip()
                if not url.startswith("http://127.0.0.1:"):
                    raise RuntimeError("The editor failed to open on loopback.")
                subprocess.run(["node", "tests/media-workflow.mjs", url, str(args.playwright.resolve()),
                                str(args.browser.absolute()), str(fixtures)], cwd=APP, env=env, check=True, timeout=420)
                verify_downloads(fixtures)
            except Exception:
                errors.seek(0)
                print(errors.read()[-8000:], file=sys.stderr)
                raise
            finally:
                if server.poll() is None:
                    server.terminate()
                server.communicate(timeout=30)


if __name__ == "__main__":
    main()
