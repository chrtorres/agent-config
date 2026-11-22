"""Create portable model variants and a runtime manifest for a planting fixture."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy


def generate(output):
    public = output / "public" / "plant-fixture"
    public.mkdir(parents=True)
    varieties = {}
    for name, color, span, drop in [
        ("rounded", (.83, .46, .56), .86, .16),
        ("spreading", (.58, .22, .39), 1.19, .23),
        ("pendant", (.72, .62, .77), .90, .59),
    ]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.object.empty_add()
        root = bpy.context.object
        root.name = "Specimen"
        bpy.ops.mesh.primitive_cone_add(radius1=.16, radius2=.085, depth=2, location=(0, 0, 1))
        trunk = bpy.context.object
        trunk.name = "Trunk"
        trunk.parent = root
        bark = bpy.data.materials.new("Bark")
        bark.diffuse_color = (.23, .12, .09, 1)
        trunk.data.materials.append(bark)
        canopy = bpy.data.materials.new("Crown")
        canopy.diffuse_color = (*color, 1)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=.39)
        first = bpy.context.object
        for index in range(13):
            angle = index * 2.39996
            radius = span * math.sqrt((index + .5) / 13)
            crown = first if index == 0 else first.copy()
            if index:
                bpy.context.collection.objects.link(crown)
            crown.name = f"Crown_{index:02}"
            crown.parent = root
            crown.location = (radius * math.cos(angle), radius * math.sin(angle), 2.32 - radius * drop)
            crown.scale.z = 1 + drop
        first.data.materials.append(canopy)
        bpy.ops.wm.save_as_mainfile(filepath=str(output / f"{name}.blend"))
        path = public / f"{name}.glb"
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True,
                                 export_gpu_instances=True, export_draco_mesh_compression_enable=True)
        data = path.read_bytes()
        size = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20:20 + size])
        extensions = set(document["extensionsUsed"])
        assert {"EXT_mesh_gpu_instancing", "KHR_draco_mesh_compression"} <= extensions
        varieties[name] = {"file": path.name, "sha256": hashlib.sha256(data).hexdigest()}
    (public / "specimens.json").write_text(json.dumps(varieties, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Existing isolated app directory")
    generate(parser.parse_args(sys.argv[sys.argv.index("--") + 1:]).output.resolve())
