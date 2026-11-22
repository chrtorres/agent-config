"""Encode the fictional portraits from the still-photo fixture as browser smoke inputs."""

import argparse
from pathlib import Path
import subprocess

import imageio_ffmpeg


def encode(portrait, destination, hide_face=False):
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
               "-nostdin", "-loop", "1", "-framerate", "12", "-i", str(portrait)]
    if hide_face:
        # The last three frames establish that a tracking gap keeps its original pixels.
        command.extend(["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-vf", "drawbox=color=black:t=fill:enable='gte(n,9)'",
                        "-c:a", "aac"])
    command.extend(["-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination)])
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_directory", type=Path)
    args = parser.parse_args()
    encode(args.fixture_directory / "source.png", args.fixture_directory / "source.mp4")
    encode(args.fixture_directory / "target.png", args.fixture_directory / "target.mp4", hide_face=True)


if __name__ == "__main__":
    main()
