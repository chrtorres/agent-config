"""Generate a synthetic multipart review and individual print files."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]).output.resolve()
    template = Path(__file__).resolve().parents[2] / "assets" / "interactive-review-viewer"
    review = output / "review"
    shutil.copytree(template, review)
    stls = output / "stls"
    stls.mkdir()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(location=(-24, 0, 5))
    plate = bpy.context.object
    plate.name = "Fixture plate"
    plate.scale = (24, 20, 5)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=19, depth=10, location=(22, 0, 5))
    pad = bpy.context.object
    pad.name = "Fixture pad.001"
    bpy.ops.mesh.primitive_torus_add(major_radius=8, minor_radius=2, location=(6, 0, 12))
    ring = bpy.context.object
    ring.name = "Fixture ring"
    parts = ((plate, "Plate", (-24, 0, 0)), (pad, "Pad", (24, 0, 0)), (ring, "Ring", (0, 20, 5)))

    bpy.context.view_layer.update()
    bounds = {}
    for part, _, _ in parts:
        vertices = [part.matrix_world @ vertex.co for vertex in part.data.vertices]
        bounds[part.name] = [[reducer(vertex[axis] for vertex in vertices) for axis in range(3)]
                             for reducer in (min, max)]
    (output / "geometry.json").write_text(json.dumps({
        "units": "mm", "part_bounds_xyz_mm": bounds,
    }, indent=2) + "\n")

    exports, definitions = [], []
    for index, (part, label, offset) in enumerate(parts):
        file = stls / f"piece-{index + 1}.stl"
        bpy.ops.object.select_all(action="DESELECT")
        part.select_set(True)
        bpy.ops.wm.stl_export(filepath=str(file), export_selected_objects=True,
                              forward_axis="Y", up_axis="Z", use_scene_unit=False)
        exports.append({"file": file.relative_to(output).as_posix(), "label": label,
                        "offset": list(offset), "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
        x, y, z = offset
        definitions.append({"node": part.name, "label": label, "offset": [x, z, -y]})

    # Represent one inspectable part as a named group with a child mesh.
    bpy.ops.object.empty_add()
    ring_group = bpy.context.object
    ring.name = "Fixture ring mesh"
    ring_group.name = definitions[-1]["node"]
    ring.parent = ring_group

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, -23, 11))
    guide = bpy.context.object
    guide.name = "Fixture assembly guide"
    guide.scale = (40, 1, 1)
    bpy.ops.export_scene.gltf(filepath=str(review / "model.glb"), export_format="GLB")
    title = "Synthetic plate, pad, and ring"
    (review / "metadata.json").write_text(json.dumps({
        "title": title,
        "facts": {"Version": "fixture", "Units": "millimeters"},
        "parts": definitions,
    }, indent=2) + "\n")
    (output / "print-preview.json").write_text(json.dumps({
        "title": title, "version": "fixture", "units": "millimeters", "parts": exports,
    }, indent=2) + "\n")

    bpy.ops.object.camera_add(location=(80, -135, 130))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 800, 600
    scene.render.filepath = str(output / "assembly.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "fixture.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
