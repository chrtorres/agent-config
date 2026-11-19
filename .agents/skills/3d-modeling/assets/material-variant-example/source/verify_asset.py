"""Check the authored anatomy and reimport the delivered GLB in Blender."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("version", type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
version = args.version.resolve()
report = json.loads((version/"evidence/geometry.json").read_text())
texture_size = tuple(report["texture_size"])
asset = version/"review/model.glb"
raw = asset.read_bytes()
magic, schema, size, json_size, json_tag = struct.unpack_from("<4sIII4s", raw)
assert (magic,schema,size,json_tag) == (b"glTF",2,len(raw),b"JSON")
document = json.loads(raw[20:20+json_size])
assert not any("uri" in payload for payload in document["images"]+document["buffers"])
assert len(document["images"]) == 3
body = next(material for material in document["materials"] if material["name"].startswith("Skin"))
pbr = body["pbrMetallicRoughness"]
assert "baseColorTexture" in pbr and "metallicRoughnessTexture" in pbr and "normalTexture" in body
assert pbr.get("metallicFactor",1) > 0
assert len(document["meshes"]) == len(report["pieces"]) == 14
assert sum("COLOR_0" in part["attributes"] for mesh in document["meshes"] for part in mesh["primitives"]) == 9
del raw


def measure(objects):
    points = np.asarray([obj.matrix_world@v.co for obj in objects for v in obj.data.vertices])
    assert np.isfinite(points).all()
    return (points.max(axis=0)-points.min(axis=0))*1000


bpy.ops.wm.open_mainfile(filepath=str(version/(report["variety"]+".blend")))
authored = list(bpy.data.collections["Nishikigoi anatomy"].objects)
assert Counter(obj.name for obj in authored) == Counter(item["name"] for item in report["pieces"])
assert np.allclose(measure(authored),report["dimensions_mm"],atol=.002,rtol=0)
for obj in authored:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert all(face.calc_area() > 0 for face in bm.faces), obj.name
    assert bm.calc_volume(signed=True) > 0, obj.name
    # A closed anatomical surface must also be connected within its named mesh.
    seed = next(iter(bm.verts))
    visited = {seed}
    pending = [seed]
    while pending:
        current = pending.pop()
        for edge in current.link_edges:
            neighbor = edge.other_vert(current)
            if neighbor not in visited:
                visited.add(neighbor)
                pending.append(neighbor)
    assert len(visited) == len(bm.verts), obj.name
    bm.free()
assert sum(bool(im.packed_file) and tuple(im.size) == texture_size for im in bpy.data.images) == 3

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(asset))
imported = list(bpy.context.scene.objects)
assert all(obj.type == "MESH" for obj in imported)
assert len(imported) == 14
assert sum(tuple(im.size) == texture_size for im in bpy.data.images) >= 3
assert np.allclose(measure(imported),report["dimensions_mm"],atol=.002,rtol=0)
for obj in imported:
    obj.data.calc_loop_triangles()
triangles = sum(len(obj.data.loop_triangles) for obj in imported)
assert triangles == sum(piece["triangles"] for piece in report["pieces"])
result = {"blender":bpy.app.version_string, "glb_sha256":hashlib.sha256(asset.read_bytes()).hexdigest(),
          "dimensions_mm":report["dimensions_mm"],"anatomical_meshes":len(imported),
          "triangles":triangles, "variety":report["variety"],
          "embedded_pbr_maps":{"size":texture_size,"maps":["base color","normal","roughness/metallic"]},
          "studio_objects_in_glb":0, "authored_shells":"closed, connected and outward-facing"}
print(json.dumps(result,indent=2))
