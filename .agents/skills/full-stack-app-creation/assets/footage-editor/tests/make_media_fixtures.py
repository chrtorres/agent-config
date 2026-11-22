"""Make short format variants from an authorized, visible-performer test clip."""
import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.media import ffmpeg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--start", type=float, default=0)
    args = parser.parse_args()
    args.destination.mkdir()
    artwork = Image.new("RGB", (100, 50), (119, 82, 142))
    ImageDraw.Draw(artwork).rectangle((20, 10, 50, 30), fill=(51, 137, 100))
    for extension in ("png", "jpg", "webp"):
        artwork.save(args.destination / f"still.{extension}")

    # MP4 is the only accepted video container. The WebM and MOV cases check that other
    # formats are rejected rather than converted.
    cases = {
        "mp4.mp4": ("-c:v", "libx264", "-c:a", "aac"),
        "silent.mp4": ("-c:v", "libx264", "-an"),
        "webm.webm": ("-c:v", "libvpx-vp9", "-c:a", "libopus"),
        "mov.mov": ("-c:v", "libx264", "-c:a", "aac"),
    }
    for name, encoding in cases.items():
        ffmpeg("-loglevel", "error", "-ss", args.start, "-i", args.source,
               "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
               "-t", "1.2", "-map", "0:v:0", "-map", "1:a:0",
               "-vf", "scale=360:640:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=25",
               "-threads:v", "4", "-pix_fmt", "yuv420p", *encoding, args.destination / name)

    # A display-matrix rotation exercises the MP4 orientation preparation step.
    ffmpeg("-loglevel", "error", "-display_rotation", "90", "-i", args.destination / "mp4.mp4",
           "-c", "copy", args.destination / "rotated.mp4")


if __name__ == "__main__":
    main()
