"""Compare two GLB exports by decoded content rather than container bytes.

    python3 compare_glb_exports.py <a.glb> <b.glb>

Regenerated Blender exports often differ in byte layout while carrying identical
geometry. This compares, per mesh primitive, a canonical triangle set (each triangle's
vertices sorted, then the triangle list sorted, positions rounded to 1e-7), plus node
names/translations/rotations and the animation channel layout. Exit status 1 on any
MISMATCH. Needs numpy.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

COMPONENT = {5126: "f4", 5125: "u4", 5123: "u2", 5121: "u1"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def decode(path):
    data = Path(path).read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + n])
    binary = data[20 + n + 8:]

    def accessor(i):
        a = gltf["accessors"][i]
        view = gltf["bufferViews"][a["bufferView"]]
        width = WIDTH[a["type"]]
        start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(binary, dtype=COMPONENT[a["componentType"]],
                             count=a["count"] * width, offset=start).reshape(-1, width)

    meshes = {}
    for mesh in gltf.get("meshes", []):
        for k, prim in enumerate(mesh["primitives"]):
            pos = accessor(prim["attributes"]["POSITION"])
            idx = accessor(prim["indices"]).ravel() if "indices" in prim else np.arange(len(pos))
            tris = sorted(tuple(sorted(map(tuple, t)))
                          for t in pos[idx].reshape(-1, 3, 3).round(7).tolist())
            meshes[f"{mesh.get('name')}#{k}"] = hashlib.sha256(repr(tris).encode()).hexdigest()
    nodes = [(x.get("name"), x.get("translation"), x.get("rotation")) for x in gltf.get("nodes", [])]
    anims = [(x.get("name"), len(x["channels"]), len(x["samplers"])) for x in gltf.get("animations", [])]
    return meshes, nodes, anims


def compare(a, b):
    ma, na, aa = decode(a)
    mb, nb, ab = decode(b)
    return [
        (ma == mb, f"canonical triangle sets ({len(ma)} primitives)"),
        (na == nb, f"node names, translations and rotations ({len(na)} nodes)"),
        (aa == ab, f"animation layout {aa}"),
    ]


if __name__ == "__main__":
    results = compare(sys.argv[1], sys.argv[2])
    for ok, label in results:
        print(f"{'MATCH' if ok else 'MISMATCH'} {label}")
    sys.exit(0 if all(ok for ok, _ in results) else 1)
