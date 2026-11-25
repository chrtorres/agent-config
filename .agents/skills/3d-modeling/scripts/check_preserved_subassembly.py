"""Compare selected mesh geometry and local transforms across two Blend files.

Run with Blender so the script can read authored mesh data without exporting it:

    blender -b --python check_preserved_subassembly.py -- \
      <source.blend> <candidate.blend> --prefix "Approved part"

The check intentionally ignores materials. A revision may restage or recolour an
approved subassembly while keeping its authored mesh and assembly pose exact.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy


def parse_property(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected KEY=VALUE")
    return value.split("=", 1)


def selected_objects(path, prefixes, required_property):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    objects = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.name.startswith(tuple(prefixes)):
            continue
        if required_property and str(obj.get(required_property[0])) != required_property[1]:
            continue
        objects[obj.name] = obj
    if not objects:
        raise ValueError(f"No selected mesh objects in {path}")
    return objects


def update_hash(digest, values):
    for value in values:
        digest.update(struct.pack("<d", float(value)))


def object_signature(obj):
    digest = hashlib.sha256()
    digest.update(obj.name.encode("utf-8"))
    update_hash(digest, (component for row in obj.matrix_local for component in row))
    for vertex in obj.data.vertices:
        update_hash(digest, vertex.co)
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", index))
    return {
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "sha256": digest.hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--prefix", action="append", required=True,
                        help="Object-name prefix to include. Repeat for multiple families.")
    parser.add_argument("--candidate-property", type=parse_property,
                        help="Optional KEY=VALUE property required only on candidate objects.")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source_path = args.source.resolve(strict=True)
    candidate_path = args.candidate.resolve(strict=True)
    source = {name: object_signature(obj) for name, obj in
              selected_objects(source_path, args.prefix, None).items()}
    candidate = {name: object_signature(obj) for name, obj in
                 selected_objects(candidate_path, args.prefix, args.candidate_property).items()}
    result = {
        "source": str(source_path),
        "candidate": str(candidate_path),
        "objects": sorted(source),
        "match": source == candidate,
        "missing": sorted(source.keys() - candidate.keys()),
        "extra": sorted(candidate.keys() - source.keys()),
        "changed": sorted(name for name in source.keys() & candidate.keys()
                          if source[name] != candidate[name]),
    }
    print(json.dumps(result, indent=2))
    if not result["match"]:
        raise ValueError("Selected mesh geometry or local transforms differ.")


if __name__ == "__main__":
    main()
