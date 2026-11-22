"""Merge every animation in a binary glTF (GLB) into one named clip, in place.

    python3 merge_glb_animations.py <model.glb> "<clip name>"

Blender's glTF exporter writes one animation per animated object. A review viewer
that offers a single clip (for example a joint exercise) needs those channels in one
animation. Only the JSON chunk is rewritten; the binary chunk is kept byte for byte,
so accessor offsets stay valid. Sampler indices are renumbered per source animation.
"""
import json
import struct
import sys
from pathlib import Path


def merge(path, name):
    data = Path(path).read_bytes()
    magic, version, _length = struct.unpack_from("<4sII", data, 0)
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if magic != b"glTF" or version != 2 or json_type != b"JSON":
        raise ValueError(f"{path} is not a glTF 2.0 binary with a leading JSON chunk")
    gltf = json.loads(data[20:20 + json_length])
    rest = data[20 + json_length:]
    channels, samplers = [], []
    for animation in gltf.get("animations", []):
        offset = len(samplers)
        samplers.extend(animation["samplers"])
        for channel in animation["channels"]:
            channel = dict(channel)
            channel["sampler"] += offset
            channels.append(channel)
    if not channels:
        raise ValueError(f"{path} has no animation channels to merge")
    gltf["animations"] = [{"name": name, "channels": channels, "samplers": samplers}]
    chunk = json.dumps(gltf, separators=(",", ":")).encode()
    chunk += b" " * (-len(chunk) % 4)  # JSON chunk must be 4-byte aligned, space padded
    body = struct.pack("<I4s", len(chunk), b"JSON") + chunk + rest
    Path(path).write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    return len(channels)


if __name__ == "__main__":
    print(f"merged {merge(sys.argv[1], sys.argv[2])} channels into '{sys.argv[2]}'")
