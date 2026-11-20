"""Create and verify frame-preserving native and portrait UHD MP4s."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import av
import imageio_ffmpeg


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-nostdin",
                    *map(str, args)], check=True)


def write_atomically(path, writer):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as scratch:
        pending = Path(scratch) / path.name
        writer(pending)
        pending.replace(path)


def mp4_boxes(file, start, end):
    file.seek(start)
    while file.tell()+8 <= end:
        offset = file.tell()
        count, kind = struct.unpack(">I4s", file.read(8))
        data = offset+8
        if count == 1:
            count = struct.unpack(">Q", file.read(8))[0]
            data += 8
        finish = end if count == 0 else offset+count
        if finish < data or finish > end:
            raise ValueError("Invalid MP4 box size")
        yield kind, (data, finish)
        file.seek(finish)


def audio_tables(file):
    end = file.seek(0, 2)
    movie = dict(mp4_boxes(file, 0, end))[b"moov"]
    for kind, track in mp4_boxes(file, *movie):
        if kind != b"trak":
            continue
        media = dict(mp4_boxes(file, *track))[b"mdia"]
        fields = dict(mp4_boxes(file, *media))
        file.seek(fields[b"hdlr"][0]+8)
        if file.read(4) != b"soun":
            continue
        entry = dict(mp4_boxes(file, *fields[b"minf"]))[b"stbl"]
        sample_times = dict(mp4_boxes(file, *entry))[b"stts"]
        return fields[b"mdhd"], sample_times
    raise ValueError("Audio track unavailable")


def audio_payloads(path):
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        return stream.codec_context.extradata, [bytes(p) for p in container.demux(stream) if p.size]


def restore_audio_timing(source, output):
    # FFmpeg stream-copy can expand the last AAC packet duration using the
    # demuxed edit list. Restore the stored AAC durations without shifting any
    # sample offsets. Only apply to a remux with the same AAC bytes and time base.
    if audio_payloads(source) != audio_payloads(output):
        raise ValueError("MP4 remux changed audio samples")
    with source.open("rb") as original, output.open("r+b") as remux:
        ref_header, ref_times = audio_tables(original)
        out_header, out_times = audio_tables(remux)
        original.seek(ref_header[0])
        remux.seek(out_header[0])
        ref_version, out_version = original.read(1), remux.read(1)
        if ref_version != out_version or ref_version not in (b"\x00", b"\x01"):
            raise ValueError("MP4 media header versions differ")
        header_fields = 12 if ref_version == b"\x00" else 20
        duration_bytes = 4 if ref_version == b"\x00" else 8
        original.seek(ref_header[0]+header_fields)
        remux.seek(out_header[0]+header_fields)
        if original.read(4) != remux.read(4):
            raise ValueError("MP4 audio timescales differ")
        if ref_times[1]-ref_times[0] != out_times[1]-out_times[0]:
            raise ValueError("MP4 sample timing table sizes differ")
        remux.write(original.read(duration_bytes))
        original.seek(ref_times[0])
        remux.seek(out_times[0])
        remux.write(original.read(ref_times[1]-ref_times[0]))


def build(source, output):
    native, uhd = output / "native.mp4", output / "4k.mp4"
    write_atomically(native, lambda target: shutil.copyfile(source, target))
    # A sharpened Lanczos upscale preserves the portrait composition, cadence
    # and soundtrack. Explicit timing prevents rate conversion at the encoder.
    def upscale(target):
        ffmpeg("-loglevel", "error", "-copyts", "-i", source, "-map", "0:v:0", "-map", "0:a:0",
               "-vf", "scale=2160:3840:flags=lanczos,unsharp=5:5:0.22:5:5:0",
               "-sws_flags", "lanczos", "-fps_mode", "passthrough", "-c:v", "libx264",
               "-threads:v", "5", "-filter_threads", "2", "-preset", "ultrafast", "-crf", "16",
               "-pix_fmt", "yuv420p", "-c:a", "copy", "-map_metadata", "-1", "-map_chapters", "-1",
               "-movflags", "+faststart", target)
        restore_audio_timing(source, target)

    write_atomically(uhd, upscale)


def inspect(path):
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        dimensions = [video.width, video.height]
        duration = video.duration * video.time_base
        timestamps = []
        for frame in container.decode(video):
            timestamps.append(frame.pts * frame.time_base)
    audio = hashlib.sha256()
    with av.open(str(path)) as container:
        for packet in container.demux(*container.streams.audio):
            if packet.stream.type == "audio" and packet.size:
                time = packet.time_base
                audio.update(f"{packet.pts*time}/{packet.dts*time}/{packet.duration*time}/".encode())
                audio.update(bytes(packet))
    decoded = hashlib.sha256()
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            decoded.update(f"{frame.pts*frame.time_base}/{frame.samples}/".encode())
            decoded.update(frame.to_ndarray().tobytes())
    return dimensions, duration, timestamps, audio.digest(), decoded.digest()


def verify(source, output):
    native = (output / "native.mp4").read_bytes() == source.read_bytes()
    original, uhd = inspect(source), inspect(output / "4k.mp4")
    report = {
        "native_file_exact": native,
        "native_dimensions": original[0],
        "uhd_dimensions": uhd[0],
        "frame_count": len(original[2]),
        "presentation_timestamps_exact": original[2] == uhd[2],
        "video_duration_exact": original[1] == uhd[1],
        "audio_packets_and_timing_exact": original[3] == uhd[3],
        "decoded_audio_samples_and_timing_exact": original[4] == uhd[4],
        "duration_seconds": float(original[1]),
    }
    print(json.dumps(report, indent=2))
    if not all((native, uhd[0] == [2160, 3840], original[1:] == uhd[1:])):
        raise SystemExit("Media validation failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "verify"])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    (build if args.action == "build" else verify)(args.source, args.output)
