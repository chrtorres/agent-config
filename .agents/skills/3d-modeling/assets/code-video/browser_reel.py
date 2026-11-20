"""Encode a captured PNG sequence and verify the resulting MP4 in Chromium."""

from argparse import ArgumentParser
from fractions import Fraction
from json import dumps, loads
from pathlib import Path
from subprocess import check_output
from urllib.request import Request, urlopen

import av
from PIL import Image

from smoke import Session, browser, eventually, serve


def encode(frames, output, width, height, fps):
    with av.open(str(output), mode="w", options={"movflags": "+faststart"}) as target:
        stream = target.add_stream("libx264", rate=fps)
        stream.width, stream.height = width, height
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "17", "preset": "fast"}
        for index, path in enumerate(frames):
            with Image.open(path) as image:
                assert image.size == (width, height), f"Unexpected frame size: {path.name}"
                frame = av.VideoFrame.from_image(image.convert("RGB"))
            frame.pts, frame.time_base = index, Fraction(1, fps)
            for packet in stream.encode(frame):
                target.mux(packet)
        for packet in stream.encode():
            target.mux(packet)

    with av.open(str(output)) as encoded:
        stream = encoded.streams.video[0]
        assert (stream.width, stream.height, stream.average_rate) == (width, height, fps)
        assert stream.codec_context.name == "h264"
        assert not encoded.streams.audio
        assert [frame.pts * frame.time_base for frame in encoded.decode(video=0)] == [
            Fraction(index, fps) for index in range(len(frames))
        ]


def check_playback(chrome, directory, width, height, count, fps):
    (directory / "index.html").write_text(
        '<!doctype html><title>Reel review</title><link rel="icon" href="data:,"><video src="reel.mp4" controls preload="auto"></video>'
    )
    with serve(directory) as address, browser(chrome) as socket:
        with urlopen(Request(address + "reel.mp4", headers={"Range": "bytes=0-31"}), timeout=5) as response:
            assert response.status == 206 and response.headers.get_content_type() == "video/mp4"
            assert len(response.read()) == 32 and response.headers["Content-Range"].startswith("bytes 0-31/")
        session = Session(socket)
        session.call("Page.navigate", url=address)
        eventually(lambda: session.script('document.querySelector("video")?.readyState >= 2'))
        times = [count / fps / 4, count / fps * 3 / 4]
        observation = session.script("""(async times => {
          const video = document.querySelector("video");
          const canvas = document.createElement("canvas");
          canvas.width = 64;
          canvas.height = 36;
          const ctx = canvas.getContext("2d");
          const timesShown = [], pixels = [];
          for (const time of times) {
            await new Promise(resolve => {
              video.addEventListener("seeked", resolve, {once: true});
              video.currentTime = time;
            });
            timesShown.push(video.currentTime);
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            pixels.push(Array.from(ctx.getImageData(0, 0, canvas.width, canvas.height).data));
          }
          const changed = pixels[0].filter((value, index) => value !== pixels[1][index]).length;
          const nonblank = pixels.every(frame => new Set(frame.filter((_, i) => i % 4 === 0)).size > 2);
          return { width: video.videoWidth, height: video.videoHeight, duration: video.duration,
                   timesShown, changed, nonblank };
        })(""" + dumps(times) + ")")
        assert (observation["width"], observation["height"]) == (width, height)
        assert abs(observation["duration"] - count / fps) < .001
        assert all(abs(actual - expected) < .001 for actual, expected in zip(observation["timesShown"], times))
        assert observation["nonblank"] and observation["changed"] > 32, observation
        return observation


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--chrome", required=True)
    args = parser.parse_args()
    timeline = loads((args.frames / "timeline.json").read_text())
    width, height, fps, count = (timeline[key] for key in ("width", "height", "fps", "count"))
    assert all(type(value) is int and value > 0 for value in (width, height, fps, count))
    assert width % 2 == height % 2 == 0 and count >= 4
    frames = [args.frames / f"frame-{index:04d}.png" for index in range(count)]
    assert set(frames) == set(args.frames.glob("frame-*.png")), "Frame sequence has missing or extra files"
    args.output_directory.mkdir()
    encode(frames, args.output_directory / "reel.mp4", width, height, fps)
    playback = check_playback(args.chrome, args.output_directory, width, height, count, fps)
    result = dumps({
        "browser": check_output([args.chrome, "--version"], text=True).strip(),
        "codec": "h264", "frames": count, "fps": fps, "playback": playback,
    }, indent=2)
    (args.output_directory / "verification.json").write_text(result + "\n")
    print(result)


if __name__ == "__main__":
    main()
