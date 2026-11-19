"""Validate a runtime character export in an isolated Blender process."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--asset", type=Path, required=True)
parser.add_argument("--metadata", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

data = args.asset.read_bytes()
magic, version, size, chunk_size, chunk_type = struct.unpack_from("<4sIII4s", data)
assert (magic, version, size, chunk_type) == (b"glTF", 2, len(data), b"JSON")
manifest = json.loads(data[20:20 + chunk_size])
assert not any("uri" in item for key in ("buffers", "images") for item in manifest.get(key, []))
assert not manifest.get("cameras") and "KHR_lights_punctual" not in manifest.get("extensionsUsed", [])
contract = json.loads(args.metadata.read_text(encoding="utf-8"))["contract"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.asset.resolve()))
root = bpy.data.objects[contract["root"]]
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert meshes and all(obj in root.children_recursive for obj in meshes)
assert all(obj.type not in {"LIGHT", "CAMERA"} for obj in bpy.context.scene.objects)
bounds = [obj.matrix_world @ Vector(point) for obj in meshes for point in obj.bound_box]
low = min(point.z for point in bounds)
height = max(point.z for point in bounds) - low
assert abs(low) < .003 and abs(height - contract["height_m"]) < .003, (low, height)
for name in contract["pivots"]:
    pivot = bpy.data.objects[name]
    assert pivot.parent == root
    limb = next(obj for obj in meshes if obj.parent == pivot)
    original = pivot.matrix_basis.copy()
    before = [limb.matrix_world @ vertex.co for vertex in limb.data.vertices]
    # Imported glTF objects may store rotations as quaternions.
    pivot.matrix_basis = original @ Matrix.Rotation(.35, 4, "X")
    bpy.context.view_layer.update()
    assert max((limb.matrix_world @ vertex.co - point).length
               for vertex, point in zip(limb.data.vertices, before)) > .001, name
    pivot.matrix_basis = original
    bpy.context.view_layer.update()
print(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "height_m": height,
                  "ground_offset_m": low, "meshes": len(meshes),
                  "triangles": sum(len(face.vertices) - 2 for obj in meshes for face in obj.data.polygons),
                  "pivots_moved": contract["pivots"], "external_uris": 0}, indent=2))
