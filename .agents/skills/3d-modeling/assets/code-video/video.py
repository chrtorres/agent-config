"""Generate, remux, or compare a video with Python and PyAV."""

from argparse import ArgumentParser
from fractions import Fraction
from hashlib import sha256
from json import dumps
from math import sin, tau
from pathlib import Path
from tempfile import TemporaryDirectory

import av
import numpy as np
from PIL import Image, ImageDraw

SIZE = (320, 240)
FPS = 12
FRAMES = 24
SAMPLE_RATE = 48000


def draw_frame(index):
    image = Image.new("RGB", SIZE, "#142131")
    draw = ImageDraw.Draw(image)
    draw.line((20, 120, 300, 120), fill="#4d657f", width=3)
    x = 48 + 9 * index
    y = 120 + round(48 * sin(tau * index / FRAMES))
    draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill="#ffc15a")
    return image


def encode(destination, frames_dir):
    paths = sorted(frames_dir.glob("frame-*.png")) if frames_dir else []
    if frames_dir and not paths:
        raise ValueError("Expected zero-padded frame-*.png images")
    count = len(paths) if frames_dir else FRAMES
    with av.open(destination, "w", format="mp4", options={"movflags": "+faststart"}) as output:
        video = output.add_stream("libx264", rate=FPS, options={"crf": "18", "preset": "medium"})
        video.width, video.height = SIZE
        video.pix_fmt = "yuv420p"
        audio = output.add_stream("aac", rate=SAMPLE_RATE)
        audio.layout = "mono"
        samples_per_frame = SAMPLE_RATE // FPS
        for index in range(count):
            if frames_dir:
                with Image.open(paths[index]) as loaded:
                    image = loaded.convert("RGB")
            else:
                image = draw_frame(index)
            if image.size != SIZE:
                raise ValueError(f"Frame {index} must be {SIZE[0]} × {SIZE[1]}")
            frame = av.VideoFrame.from_image(image)
            frame.pts, frame.time_base = index, Fraction(1, FPS)
            output.mux(video.encode(frame))

            # The oscillator uses absolute sample indexes to stay phase-continuous across frames.
            start = index * samples_per_frame
            times = np.arange(start, start + samples_per_frame) / SAMPLE_RATE
            signal = (0.12 * np.sin(tau * 440 * times)).astype("float32")
            sound = av.AudioFrame.from_ndarray(signal[np.newaxis, :], format="fltp", layout="mono")
            sound.pts, sound.time_base, sound.sample_rate = start, Fraction(1, SAMPLE_RATE), SAMPLE_RATE
            output.mux(audio.encode(sound))
        output.mux(video.encode(None))
        output.mux(audio.encode(None))


def remux(source, destination):
    with av.open(source) as incoming, av.open(
        destination, "w", format="mp4", options={"movflags": "+faststart"},
    ) as output:
        inputs = [stream for stream in incoming.streams if stream.type in {"video", "audio"}]
        if sorted(stream.type for stream in inputs) != ["audio", "video"]:
            raise ValueError("The example expects one video and one audio stream")
        outputs = {stream.index: output.add_stream_from_template(stream) for stream in inputs}
        for packet in incoming.demux(inputs):
            # Keep negative timestamps. They can represent decoder lead-in or AAC priming.
            if packet.dts is not None:
                packet.stream = outputs[packet.stream.index]
                output.mux(packet)


def inspect(path):
    report = {}
    for kind in ("video", "audio"):
        digest = sha256()
        packet_digest = sha256()
        with av.open(path) as media:
            stream = getattr(media.streams, kind)[0]
            codec = stream.codec_context.name
            for packet in media.demux(stream):
                if packet.dts is not None:
                    duration = None if packet.duration is None else str(packet.duration * packet.time_base)
                    timing = (
                        None if packet.pts is None else str(packet.pts * packet.time_base),
                        str(packet.dts * packet.time_base), duration, packet.is_keyframe,
                    )
                    packet_digest.update(dumps(timing).encode())
                    packet_digest.update(bytes(packet))

        timestamps, images = [], []
        samples = 0
        with av.open(path) as media:
            for frame in media.decode(**{kind: 0}):
                timestamps.append(str(frame.pts * frame.time_base))
                if kind == "video":
                    # RGB conversion discards decoder row padding and gives a stable display representation.
                    pixels = frame.to_ndarray(format="rgb24").tobytes()
                    images.append(sha256(pixels).hexdigest())
                    digest.update(pixels)
                else:
                    samples += frame.samples
                    digest.update(frame.to_ndarray().tobytes())
            stream = getattr(media.streams, kind)[0]
            metadata = (
                {"width": stream.width, "height": stream.height, "rate": str(stream.average_rate)}
                if kind == "video" else {"rate": stream.rate, "channels": stream.channels}
            )
        if not timestamps:
            raise ValueError(f"No decoded {kind} frames")
        report[kind] = {
            **metadata, "codec": codec, "frames": len(timestamps), "timestamps": timestamps,
            "decoded_sha256": digest.hexdigest(), "encoded_timing_sha256": packet_digest.hexdigest(),
        }
        if kind == "video":
            report[kind]["distinct_images"] = len(set(images))
        else:
            report[kind]["samples_per_channel"] = samples
    return report


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("output", type=Path)
    generate.add_argument("--frames-dir", type=Path)
    copy = commands.add_parser("remux")
    copy.add_argument("source", type=Path)
    copy.add_argument("output", type=Path)
    check = commands.add_parser("inspect")
    check.add_argument("source", type=Path)
    check.add_argument("--compare", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        first = inspect(args.source)
        if args.compare:
            if first != inspect(args.compare):
                parser.exit(1, "Decoded content, format, packets or timing differ\n")
            first = {"streams": first, "container_bytes_equal": args.source.read_bytes() == args.compare.read_bytes()}
        print(dumps(first, indent=2))
        return
    if args.command == "remux" and args.source.resolve() == args.output.resolve():
        parser.error("Use a different destination for the remux")
    with TemporaryDirectory(dir=args.output.parent) as directory:
        staged = Path(directory) / "video.mp4"
        if args.command == "generate":
            encode(staged, args.frames_dir)
        else:
            remux(args.source, staged)
        staged.replace(args.output)


if __name__ == "__main__":
    main()
