"""Combine independent fragmented tracks without making FFmpeg retime AAC."""
from fractions import Fraction
import io
from itertools import chain
import struct

import av

if __package__:
    from .media import mp4_boxes
else:
    from media import mp4_boxes


FRAGMENTED = "+frag_keyframe+empty_moov+default_base_moof"


def fragment_audio(source, output, durations, movie_clock=None):
    schedule = iter(durations)
    with av.open(str(source)) as original:
        audio = original.streams.audio[0]
        packets = (packet for packet in original.demux(audio) if packet.size)
        first = next(packets, None)
        if first is None:
            raise ValueError("The audio track contains no AAC packets.")
        # An edit list is required when AAC priming gives the first packet a
        # nonzero DTS. Empty movie headers otherwise shift it to zero.
        flags = FRAGMENTED.replace("empty_moov", "delay_moov") if first.dts else FRAGMENTED
        options = {"movflags":flags}
        if movie_clock is not None:
            options["movie_timescale"] = str(movie_clock)
        with av.open(str(output), "w", options=options) as result:
            track = result.add_stream_from_template(audio)
            for packet in chain((first,), packets):
                duration = next(schedule, None)
                if duration is None:
                    raise ValueError("The AAC packet count does not match its fragment tables.")
                packet.duration = duration
                packet.stream = track
                result.mux(packet)
            if next(schedule, None) is not None:
                raise ValueError("The AAC fragment tables contain unconsumed samples.")


def box(kind, data):
    return struct.pack(">I4s", len(data) + 8, kind) + data


def contents(data, kind):
    stream = io.BytesIO(data)
    return dict(mp4_boxes(stream, 0, len(data)))[kind]


def replace_u32(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def audio_sample_durations(path):
    """Read stored fragment durations before a demuxer applies AAC heuristics."""
    def u32(data, offset):
        return struct.unpack_from(">I", data, offset)[0]

    with path.open("rb") as file:
        regions = list(mp4_boxes(file, 0, file.seek(0, 2)))

        def read(region):
            file.seek(region[0])
            return file.read(region[1] - region[0])

        movie = dict(regions)[b"moov"]
        for kind, region in mp4_boxes(file, *movie):
            if kind != b"trak":
                continue
            track = read(region)
            media = contents(track, b"mdia")
            handler = contents(track[media[0]:media[1]], b"hdlr")[0]
            if track[media[0] + handler + 8:media[0] + handler + 12] == b"soun":
                header = contents(track, b"tkhd")[0]
                audio_id = u32(track, header + (20 if track[header] else 12))
                break
        else:
            raise ValueError("No audio track found in fragmented MP4.")
        extension = dict(mp4_boxes(file, *movie))[b"mvex"]
        defaults = [data for kind, region in mp4_boxes(file, *extension)
                    if kind == b"trex" and u32(data := read(region), 4) == audio_id]
        default_duration = u32(defaults[0], 12) if defaults else 0
        durations = []
        for kind, region in regions:
            if kind != b"moof":
                continue
            for member, fragment in mp4_boxes(file, *region):
                if member != b"traf":
                    continue
                fields = list(mp4_boxes(file, *fragment))
                header = read(dict(fields)[b"tfhd"])
                if u32(header, 4) != audio_id:
                    continue
                flags = u32(header, 0) & 0xFFFFFF
                offset = 8 + (8 if flags & 1 else 0) + (4 if flags & 2 else 0)
                duration = u32(header, offset) if flags & 8 else default_duration
                for field, bounds in fields:
                    if field == b"trun":
                        run = read(bounds)
                        flags = u32(run, 0) & 0xFFFFFF
                        count = u32(run, 4)
                        offset = 8 + (4 if flags & 1 else 0) + (4 if flags & 4 else 0)
                        if flags & 0x100:
                            stride = 4 * sum(bool(flags & key) for key in (0x100, 0x200, 0x400, 0x800))
                            durations.extend(u32(run, offset + index * stride) for index in range(count))
                        else:
                            durations.extend([duration] * count)
        return durations


def initialize(video, audio):
    def read_box(file, kind):
        region = dict(mp4_boxes(file, 0, file.seek(0, 2)))[kind]
        file.seek(region[0])
        return bytearray(file.read(region[1] - region[0]))

    header = read_box(video, b"ftyp")
    picture, sound = read_box(video, b"moov"), read_box(audio, b"moov")
    tkhd = contents(sound, b"trak")[0] + 8
    track_id = tkhd + (20 if sound[tkhd] else 12)
    replace_u32(sound, track_id, 2)
    trex = contents(sound, b"mvex")[0] + 8
    replace_u32(sound, trex + 4, 2)
    mvhd = contents(picture, b"mvhd")
    replace_u32(picture, mvhd[1] - 4, 3)
    picture_mvex = contents(picture, b"mvex")
    sound_mvex = contents(sound, b"mvex")
    sound_trak = contents(sound, b"trak")
    extensions = box(b"mvex", picture[picture_mvex[0]:picture_mvex[1]] + sound[sound_mvex[0]:sound_mvex[1]])
    movie = (picture[:picture_mvex[0]-8] + extensions + picture[picture_mvex[1]:]
             + box(b"trak", sound[sound_trak[0]:sound_trak[1]]))
    return box(b"ftyp", header) + box(b"moov", movie)


def fragments(file, clock, track_id):
    boxes = iter(mp4_boxes(file, 0, file.seek(0, 2)))
    for kind, region in boxes:
        if kind != b"moof":
            continue
        file.seek(region[0])
        moof = bytearray(file.read(region[1] - region[0]))
        traf = contents(moof, b"traf")[0]
        tfhd = traf + contents(moof[traf:], b"tfhd")[0]
        tfdt = traf + contents(moof[traf:], b"tfdt")[0]
        replace_u32(moof, tfhd + 4, track_id)
        size = 8 if moof[tfdt] else 4
        time = Fraction(int.from_bytes(moof[tfdt+4:tfdt+4+size], "big"), clock)
        mdat, payload = next(boxes)
        if mdat != b"mdat":
            raise ValueError("Unexpected MP4 fragment layout.")
        yield time, moof, payload


def merge(video_path, audio_path, output, video_clock, audio_clock):
    # Both inputs use default-base-is-moof. Relocating a complete fragment
    # preserves its sample data offsets and independent decode timeline.
    from heapq import merge as ordered
    with video_path.open("rb") as video, audio_path.open("rb") as audio, output.open("wb") as result:
        result.write(initialize(video, audio))
        picture = ((time, moof, payload, video) for time, moof, payload in fragments(video, video_clock, 1))
        sound = ((time, moof, payload, audio) for time, moof, payload in fragments(audio, audio_clock, 2))
        for sequence, (_, moof, payload, source) in enumerate(ordered(picture, sound, key=lambda row:row[0]), 1):
            replace_u32(moof, contents(moof, b"mfhd")[0] + 4, sequence)
            result.write(box(b"moof", moof))
            start, end = payload
            result.write(struct.pack(">I4s", end-start+8, b"mdat"))
            source.seek(start)
            remaining = end - start
            while remaining:
                data = source.read(min(remaining, 1024 ** 2))
                if not data:
                    raise ValueError("Incomplete MP4 fragment.")
                result.write(data)
                remaining -= len(data)
