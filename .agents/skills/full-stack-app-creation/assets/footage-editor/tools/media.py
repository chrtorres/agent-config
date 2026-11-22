"""Create and verify frame-preserving native and 4K MP4s."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from filecmp import cmp
from fractions import Fraction
from itertools import zip_longest
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import av
import imageio_ffmpeg

if __package__:
    from .progress import Progress, frame_total
else:
    from progress import Progress, frame_total


def ffmpeg(*args, progress=None):
    """Run FFmpeg. With progress, call progress(frames_written) as FFmpeg reports it."""
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-nostdin"]
    if progress is None:
        subprocess.run([*command, *map(str, args)], check=True)
        return
    # -progress writes key=value blocks about twice a second on stdout.
    with subprocess.Popen([*command, "-progress", "pipe:1", "-stats_period", "0.5", *map(str, args)],
                          stdout=subprocess.PIPE, text=True) as process:
        for line in process.stdout:
            if line.startswith("frame="):
                try:
                    progress(int(line[6:]))
                except ValueError:
                    pass
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command[0])


def encoder_threads():
    # Measured on a 6-core/12-thread host: frame-threaded x264 plus six filter threads is about
    # 1.7x faster than the earlier fixed 5/2 split for the 4K resize and sharpen chain.
    return max(2, min(8, os.cpu_count() or 2))


def presentation_offset(manifest, index):
    times = manifest.get("frameTimes")
    return times[index] if times is not None else index / manifest["fps"]


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
        track_fields = dict(mp4_boxes(file, *track))
        media = track_fields[b"mdia"]
        fields = dict(mp4_boxes(file, *media))
        file.seek(fields[b"hdlr"][0]+8)
        if file.read(4) != b"soun":
            continue
        entry = dict(mp4_boxes(file, *fields[b"minf"]))[b"stbl"]
        sample_times = dict(mp4_boxes(file, *entry))[b"stts"]
        edits = dict(mp4_boxes(file, *track_fields[b"edts"])).get(b"elst") if b"edts" in track_fields else None
        return fields[b"mdhd"], sample_times, edits
    raise ValueError("Audio track unavailable")


def audio_payloads(path):
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        return stream.codec_context.extradata, [bytes(p) for p in container.demux(stream) if p.size]


def rescale_edit_times(file, edits, source_scale, target_scale):
    if edits is None or source_scale == target_scale:
        return
    file.seek(edits[0])
    version, count = struct.unpack(">B3xI", file.read(8))
    if version not in (0, 1):
        raise ValueError("Unsupported MP4 audio edit list version")
    size = 8 if version else 4
    if edits[1] - edits[0] != 8 + count * (2 * size + 4):
        raise ValueError("Invalid MP4 audio edit list length")
    for index in range(count):
        # Only media_time is in audio ticks. Segment durations use the movie clock.
        offset = edits[0] + 8 + index * (2 * size + 4) + size
        file.seek(offset)
        media_time = int.from_bytes(file.read(size), "big", signed=True)
        if media_time == -1:
            continue
        scaled = Fraction(media_time * target_scale, source_scale)
        if scaled.denominator != 1:
            raise ValueError("MP4 audio edit time cannot be represented on the source clock")
        file.seek(offset)
        file.write(int(scaled).to_bytes(size, "big", signed=True))


def restore_audio_timing(source, output):
    # FFmpeg stream-copy can expand the last AAC packet duration using the
    # demuxed edit list. Restore the stored AAC durations without shifting any
    # sample offsets. A remux can also replace the source clock with the AAC sample rate.
    if audio_payloads(source) != audio_payloads(output):
        raise ValueError("MP4 remux changed audio samples")
    with source.open("rb") as original, output.open("r+b") as remux:
        ref_header, ref_times, _ = audio_tables(original)
        out_header, out_times, out_edits = audio_tables(remux)
        original.seek(ref_header[0])
        remux.seek(out_header[0])
        ref_version, out_version = original.read(1), remux.read(1)
        if ref_version != out_version or ref_version not in (b"\x00", b"\x01"):
            raise ValueError("MP4 media header versions differ")
        header_fields = 12 if ref_version == b"\x00" else 20
        duration_bytes = 4 if ref_version == b"\x00" else 8
        original.seek(ref_header[0]+header_fields)
        remux.seek(out_header[0]+header_fields)
        source_clock = original.read(4)
        remux_clock = remux.read(4)
        if ref_times[1]-ref_times[0] != out_times[1]-out_times[0]:
            raise ValueError("MP4 sample timing table sizes differ")
        remux.seek(out_header[0]+header_fields)
        remux.write(source_clock + original.read(duration_bytes))
        original.seek(ref_times[0])
        remux.seek(out_times[0])
        remux.write(original.read(ref_times[1]-ref_times[0]))
        rescale_edit_times(remux, out_edits, int.from_bytes(remux_clock, "big"), int.from_bytes(source_clock, "big"))


def uhd_size(width, height):
    longest = max(width, height)
    return tuple(max(2, 2 * ((side * 3840 + longest) // (2 * longest))) for side in (width, height))


def needs_normalization(video, frame):
    return bool(frame.rotation or video.sample_aspect_ratio not in (None, 0, 1)
                or video.width % 2 or video.height % 2)


MP4_ONLY = "Choose an MP4 video with H.264 video and AAC or no audio. Other formats are not converted."


def is_mp4(source):
    """Return True for an ISO base media file that is not a QuickTime movie."""
    with source.open("rb") as media:
        header = media.read(12)
    return header[4:8] == b"ftyp" and header[8:12] != b"qt  "


def require_mp4(source):
    """Validate an MP4 the editor can play directly; return whether it needs orientation normalization."""
    if not is_mp4(source):
        raise ValueError(MP4_ONLY)
    try:
        with av.open(str(source), format="mp4") as container:
            if len(container.streams.video) != 1 or len(container.streams.audio) > 1:
                raise ValueError("Choose an MP4 with one video stream and at most one audio stream.")
            video = container.streams.video[0]
            audio = next(iter(container.streams.audio), None)
            if video.codec_context.name != "h264" or (audio is not None and audio.codec_context.name != "aac"):
                raise ValueError(MP4_ONLY)
            first = next(container.decode(video), None)
            if first is None:
                raise ValueError("The recording does not contain any decodable video frames.")
            return needs_normalization(video, first)
    except av.error.FFmpegError:
        raise ValueError("Could not decode this MP4. Check that the upload is complete.") from None


def graded_video(source, output, adjustments=None):
    """Render Quick Review zoom and color onto an MP4 while retaining every decoded picture."""
    require_mp4(source)
    with av.open(str(source), format="mp4") as original:
        stream = original.streams.video[0]
        has_audio = bool(original.streams.audio)
        ratio = float(stream.sample_aspect_ratio or 1)
        total = frame_total(stream)
        first = next(original.decode(stream), None)
        if first is None:
            raise ValueError("The video does not contain any decodable frames.")
    filters = []
    if adjustments is not None and adjustments != [1, 1, 1, 1]:
        zoom, light, contrast, saturation = adjustments
        # Match the centered zoom and ordered RGB adjustments in Quick Review.
        width, height = first.width, first.height
        if first.rotation % 180:
            width, height = height, width
            ratio = 1 / ratio
        width, height = max(2, 2 * round(width * ratio / 2)), max(2, 2 * round(height / 2))
        filters.extend([f"crop=iw/{zoom}:ih/{zoom}", f"scale={width}:{height}", "setsar=1", "format=gbrp"])
        level = f"clip((clip(val*{light},0,255)-127.5)*{contrast}+127.5,0,255)"
        filters.extend([f"lutrgb=r='{level}':g='{level}':b='{level}'", f"hue=s={saturation}"])
    filters.append("scale=max(2\\,2*round(iw*if(gt(sar\\,0)\\,sar\\,1)/2)):max(2\\,2*round(ih/2)),setsar=1")
    progress = Progress(total)
    ffmpeg("-loglevel", "error", "-f", "mp4", "-i", source,
           "-map", "0:v:0", *(("-map", "0:a:0") if has_audio else ()), "-vf", ",".join(filters),
           "-fps_mode", "passthrough", "-enc_time_base", "demux", "-c:v", "libx264",
           "-threads:v", str(encoder_threads()), "-filter_threads", "4", "-crf", "0", "-pix_fmt", "yuv420p",
           "-c:a", "copy", "-map_metadata", "-1", "-movflags", "+faststart", output,
           progress=lambda frames: progress.update(frames * .9))
    with av.open(str(source), format="mp4") as old, av.open(str(output), format="mp4") as new:
        original_frames = (frame.pts * frame.time_base for frame in old.decode(video=0))
        output_frames = (frame.pts * frame.time_base for frame in new.decode(video=0))
        origin = None
        for before, after in zip_longest(original_frames, output_frames):
            if before is None or after is None:
                raise ValueError("The edited video did not retain every frame.")
            if origin is None:
                origin = before - after
            if abs(before - after - origin) > .001:
                raise ValueError("The edited video did not retain the source frame timing.")
        if origin is None:
            raise ValueError("The video does not contain any decodable frames.")
    progress.finish()


@contextmanager
def upright_source(source):
    with av.open(str(source)) as clip:
        video = clip.streams.video[0]
        first = next(clip.decode(video))
        needed = needs_normalization(video, first)
    if not needed:
        yield source
        return
    with tempfile.TemporaryDirectory(dir="/dev/shm") as directory:
        upright = Path(directory) / "upright.mp4"
        normalize(source, upright)
        yield upright


def normalize(source, output):
    with av.open(str(source)) as clip:
        has_audio = bool(clip.streams.audio)
        progress = Progress(frame_total(clip.streams.video[0]))
    # FFmpeg applies the display matrix before scaling. Round to even square-pixel dimensions for H.264.
    ffmpeg("-loglevel", "error", "-copyts", "-i", source, "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", "scale=max(2\\,2*round(iw*if(gt(sar\\,0)\\,sar\\,1)/2)):max(2\\,2*round(ih/2)),setsar=1",
           "-fps_mode", "passthrough", "-c:v", "libx264", "-threads:v", str(encoder_threads()),
           "-crf", "0", "-pix_fmt", "yuv420p",
           "-c:a", "copy", "-movflags", "+faststart", output,
           progress=lambda frames: progress.update(frames * .8))
    if has_audio:
        restore_audio_timing(source, output)
    before, after = inspect_pair(source, output)
    if before[1:] != after[1:]:
        raise ValueError("Orientation preparation changed media timing or audio")
    progress.finish()


def build(source, output, copy_native=True, progress=None):
    native, uhd = output / "native.mp4", output / "4k.mp4"
    if copy_native:
        write_atomically(native, lambda target: shutil.copyfile(source, target))
    with av.open(str(source)) as clip:
        video = clip.streams.video[0]
        width, height = uhd_size(video.width, video.height)
        fragmented = video.frames == 0
        video_clock = video.time_base.denominator
        audio_clock = clip.streams.audio[0].time_base.denominator if clip.streams.audio else None
        total = frame_total(video)

    # A sharpened Lanczos resize preserves composition while explicit timing prevents rate conversion.
    def scale_video(target, audio_args, container_args):
        ffmpeg("-loglevel", "error", "-copyts", "-i", source, "-map", "0:v:0",
               "-vf", f"scale={width}:{height}:flags=lanczos,setsar=1,unsharp=5:5:0.22:5:5:0",
               "-sws_flags", "lanczos", "-fps_mode", "passthrough", "-enc_time_base", "demux", "-c:v", "libx264",
               "-threads:v", str(encoder_threads()), "-filter_threads", str(min(6, encoder_threads())),
               "-preset", "ultrafast", "-crf", "16",
               "-pix_fmt", "yuv420p", "-map_metadata", "-1", "-map_chapters", "-1",
               *audio_args, *container_args, target,
               progress=None if progress is None else lambda frames: progress.update(frames, total * 1.25))

    def upscale(target):
        clocks = ("-movie_timescale", str(video_clock), "-video_track_timescale", str(video_clock))
        if audio_clock is None:
            scale_video(target, (), (*clocks, "-movflags", "+faststart"))
            return
        if not fragmented:
            scale_video(target, ("-map", "0:a:0", "-c:a", "copy"), (*clocks, "-movflags", "+faststart"))
            restore_audio_timing(source, target)
            return
        if __package__:
            from .face_fragments import audio_sample_durations, fragment_audio, merge
        else:
            from face_fragments import audio_sample_durations, fragment_audio, merge
        video_path, audio_path = target.with_name("picture.mp4"), target.with_name("sound.mp4")
        # The delayed movie header keeps a nonzero first video PTS. Independent
        # AAC fragments preserve the source's exact packet timing across gaps.
        scale_video(video_path, (), (*clocks, "-g", "48", "-movflags", "+frag_keyframe+delay_moov+default_base_moof"))
        fragment_audio(source, audio_path, audio_sample_durations(source), video_clock)
        merge(video_path, audio_path, target, video_clock, audio_clock)

    write_atomically(uhd, upscale)


def inspect(path, include_packet_duration=True):
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        # Frame-threaded decoding returns the same frames in the same order, several times faster at 4K.
        video.codec_context.thread_type = "AUTO"
        video.codec_context.thread_count = 0
        dimensions = [video.width, video.height]
        duration = video.duration * video.time_base
        has_audio = bool(container.streams.audio)
        timestamps = []
        for frame in container.decode(video):
            timestamps.append(frame.pts * frame.time_base)
    audio = hashlib.sha256()
    if not has_audio:
        return dimensions, duration, timestamps, None, None
    with av.open(str(path)) as container:
        for packet in container.demux(*container.streams.audio):
            if packet.stream.type == "audio" and packet.size:
                time = packet.time_base
                timing = f"{packet.pts*time}/{packet.dts*time}/"
                if include_packet_duration:
                    timing += f"{packet.duration*time}/"
                audio.update(timing.encode())
                audio.update(bytes(packet))
    decoded = hashlib.sha256()
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            decoded.update(f"{frame.pts*frame.time_base}/{frame.samples}/".encode())
            decoded.update(frame.to_ndarray().tobytes())
    return dimensions, duration, timestamps, audio.digest(), decoded.digest()


def inspect_pair(first, second, include_packet_duration=True):
    """Inspect two files concurrently. PyAV releases the GIL while decoding."""
    with ThreadPoolExecutor(2) as pool:
        jobs = [pool.submit(inspect, path, include_packet_duration) for path in (first, second)]
        return [job.result() for job in jobs]


def verify(source, output, native_is_source=False):
    native = native_is_source or cmp(output / "native.mp4", source, shallow=False)
    with av.open(str(source)) as clip:
        fragmented = clip.streams.video[0].frames == 0 and bool(clip.streams.audio)
    durations_exact = True
    if fragmented:
        if __package__:
            from .face_fragments import audio_sample_durations
        else:
            from face_fragments import audio_sample_durations
        durations_exact = audio_sample_durations(source) == audio_sample_durations(output / "4k.mp4")
    original, uhd = inspect_pair(source, output / "4k.mp4", not fragmented)
    report = {
        "native_file_exact": native,
        "native_dimensions": original[0],
        "uhd_dimensions": uhd[0],
        "frame_count": len(original[2]),
        "presentation_timestamps_exact": original[2] == uhd[2],
        "video_duration_exact": original[1] == uhd[1],
        "audio_packets_and_timing_exact": original[3] == uhd[3] and durations_exact,
        "decoded_audio_samples_and_timing_exact": original[4] == uhd[4],
        "duration_seconds": float(original[1]),
    }
    print(json.dumps(report, indent=2))
    if not all((native, tuple(uhd[0]) == uhd_size(*original[0]), original[1:] == uhd[1:], durations_exact)):
        failures = [name for name, value in report.items() if value is False]
        if tuple(uhd[0]) != uhd_size(*original[0]):
            failures.append("4k_dimensions")
        raise SystemExit("Media validation failed: " + ", ".join(failures))


def build_verified(source, output):
    build(source, output)
    verify(source, output)


def upscale_verified(source, output):
    # The editor serves the native input directly, so only the 4K rendition is generated here.
    # Encoding reports 80% of the progress and verification the remaining 20%.
    progress = Progress()
    build(source, output, copy_native=False, progress=progress)
    progress.update(progress.total * .8, force=True)
    verify(source, output, native_is_source=True)
    progress.finish()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = {"build": build, "verify": verify, "normalize": normalize, "build-verified": build_verified,
               "upscale-verified": upscale_verified, "grade": graded_video}
    parser.add_argument("action", choices=actions)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--adjustments", nargs=4, type=float)
    args = parser.parse_args()
    if args.action == "grade":
        graded_video(args.source, args.output, args.adjustments)
    else:
        actions[args.action](args.source, args.output)
