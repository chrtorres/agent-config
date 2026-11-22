"""Regression for AAC tracks whose MP4 clock differs from the sample rate."""
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

import av

from tools.media import (audio_tables, build_verified, ffmpeg, graded_video, inspect, require_mp4,
                         rescale_edit_times)


class MediaClock(unittest.TestCase):
    def test_grading_keeps_silent_variable_timing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            output = root / "graded.mp4"
            ffmpeg("-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=25:duration=0.24",
                   "-vf", "setpts=PTS+2*gte(N\\,3)", "-fps_mode", "passthrough", "-c:v", "libx264",
                   "-pix_fmt", "yuv420p", source)
            graded_video(source, output, [1.13, 1.1, 1, .9])
            with av.open(str(source)) as container:
                original = [frame.pts * frame.time_base for frame in container.decode(video=0)]
            edited = inspect(output)
            self.assertEqual(edited[0], [64, 48])
            self.assertEqual(edited[2], original)
            self.assertEqual(edited[3:], (None, None))
            self.assertGreater(len(set(b-a for a, b in zip(original, original[1:]))), 1)

    def test_other_formats_are_rejected_not_converted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cases = {"clip.webm": ("-c:v", "libvpx-vp9"), "clip.mkv": ("-c:v", "libx264"),
                     "clip.mov": ("-c:v", "libx264"), "hevc.mp4": ("-c:v", "libx265", "-x265-params", "log-level=error")}
            for name, encoding in cases.items():
                source = root / name
                ffmpeg("-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=25:duration=0.2",
                       "-pix_fmt", "yuv420p", *encoding, source)
                with self.subTest(name), self.assertRaisesRegex(ValueError, "MP4"):
                    require_mp4(source)
                with self.subTest(name + " grade"), self.assertRaisesRegex(ValueError, "MP4"):
                    graded_video(source, root / ("graded-" + name + ".mp4"))
            accepted = root / "clip.mp4"
            ffmpeg("-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=25:duration=0.2",
                   "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "0.2",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", accepted)
            self.assertFalse(require_mp4(accepted))

    def test_upscale_preserves_fragmented_video_start_offset(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "offset.mp4"
            ffmpeg("-loglevel", "error", "-copyts",
                   "-f", "lavfi", "-i", "color=size=64x48:rate=24",
                   "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                   "-vf", "settb=1/24000,setpts=PTS+3288", "-fps_mode", "passthrough",
                   "-enc_time_base", "1/24000", "-video_track_timescale", "24000", "-movie_timescale", "24000",
                   "-t", "0.5", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-movflags", "+frag_keyframe+delay_moov+default_base_moof", source)
            with av.open(str(source)) as container:
                video = container.streams.video[0]
                self.assertEqual(video.frames, 0)
                self.assertEqual(next(container.decode(video)).pts, 3288)
            build_verified(source, root / "output")

    def test_upscale_preserves_aac_on_a_480000_tick_clock(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.mp4"
            ffmpeg("-loglevel", "error", "-f", "lavfi", "-i", "color=size=64x48:rate=24",
                   "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                   "-t", "0.25", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", source)
            with source.open("r+b") as file:
                header, timing, edits = audio_tables(file)
                file.seek(header[0] + 12)
                clock, duration = struct.unpack(">II", file.read(8))
                self.assertEqual(clock, 48_000)
                file.seek(header[0] + 12)
                file.write(struct.pack(">II", clock * 10, duration * 10))
                for offset in range(timing[0] + 12, timing[1], 8):
                    file.seek(offset)
                    ticks = struct.unpack(">I", file.read(4))[0]
                    file.seek(offset)
                    file.write(struct.pack(">I", ticks * 10))
                rescale_edit_times(file, edits, clock, clock * 10)

            output = root / "output"
            build_verified(source, output)
            with av.open(str(output / "4k.mp4")) as container:
                self.assertEqual(container.streams.audio[0].time_base.denominator, 480_000)
