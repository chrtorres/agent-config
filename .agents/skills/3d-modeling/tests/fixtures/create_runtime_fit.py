"""Generate synthetic fitted and intersecting head covers with a facial morph."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--clipped", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
args.output.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
frame = bpy.data.objects.new("FitFrame", None)
bpy.context.collection.objects.link(frame)

def head():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=.1)
    mesh = bpy.context.object
    mesh.name = "HeadSurface"
    mesh.parent = frame
    mesh.shape_key_add(name="Basis")
    pose = mesh.shape_key_add(name="Expression")
    for v in pose.data:
        if v.co.y < -.06 and v.co.z > 0:
            v.co.z *= .85
    return mesh

head()
# Open toward Blender -Y and carry the rim past the widest section.
vertices = [(0, .09 if args.clipped else .12, 0)]
for ring in range(1, 11):
    angle = ring * math.pi / 18
    radius = .12 * math.sin(angle)
    depth = (.09 if args.clipped else .12) * math.cos(angle)
    for i in range(48):
        t = math.tau * i / 48
        vertices.append((radius * math.cos(t), depth, radius * math.sin(t)))
faces = [(0, 1 + i, 1 + (i + 1) % 48) for i in range(48)]
for ring in range(9):
    for i in range(48):
        a, b = 1 + 48 * ring + i, 1 + 48 * ring + (i + 1) % 48
        faces.append((a, a + 48, b + 48, b))
mesh = bpy.data.meshes.new("CoverSurface")
mesh.from_pydata(vertices, [], [tuple(reversed(face)) for face in faces])
mesh.update()
cover = bpy.data.objects.new("CoverSurface", mesh)
bpy.context.collection.objects.link(cover)
cover.parent = frame
material = bpy.data.materials.new("Fixture cover")
material.diffuse_color = (.08, .20, .38, 1)
mesh.materials.append(material)
for polygon in mesh.polygons:
    polygon.use_smooth = True
bpy.ops.export_scene.gltf(filepath=str(args.output / "model.glb"), export_format="GLB")
(args.output / "fit.json").write_text(json.dumps({
    "frame": "FitFrame", "sample_mesh": "HeadSurface", "cover_meshes": ["CoverSurface"],
    "view_direction": [0, 1, 0], "sample_bounds": [[-.11, .11], [.02, .11], [-.11, .11]],
    "min_clearance_m": .009, "min_samples": 100,
}, indent=2) + "\n", encoding="utf-8")
