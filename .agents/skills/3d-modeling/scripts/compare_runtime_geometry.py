"""Compare imported GLB triangle positions independent of export ordering."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def signature(path, decimals):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    triangles = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        coords = [tuple(round(component, decimals) or 0.0 for component in obj.matrix_world @ vertex.co)
                  for vertex in obj.data.vertices]
        # Use world coordinates and sort to remove exporter ordering and winding.
        triangles.extend(tuple(sorted(coords[index] for index in face.vertices))
                         for face in obj.data.loop_triangles)
    if not triangles:
        raise ValueError("The import contains no mesh triangles.")
    return {"triangles": len(triangles),
            "sha256": hashlib.sha256(repr(sorted(triangles)).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--decimals", type=int, choices=range(10), default=5)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    left, right = (signature(path.resolve(strict=True), args.decimals) for path in (args.left, args.right))
    print(json.dumps({"left": left, "right": right, "decimals": args.decimals, "match": left == right}))
    if left != right:
        raise ValueError("Imported triangle positions differ at the requested rounding precision.")


if __name__ == "__main__":
    main()
