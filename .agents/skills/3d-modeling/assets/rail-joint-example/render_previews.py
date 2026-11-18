"""Render the assembled cube and an enlarged corner detail from the draft."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_frame import boolean, box


def render_view(output, target, direction, scale, resolution):
    scene = bpy.context.scene
    if scene.camera is None:
        bpy.ops.object.camera_add()
        scene.camera = bpy.context.object
    camera = scene.camera
    camera.location = Vector(target) + 10 * Vector(direction).normalized()
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.studio_light = "paint.sl"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.background_type = "WORLD"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Preview background")
    scene.world.color = (0.045, 0.045, 0.045)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    render_view(output / "assembled.png", (0, 0, 0), (1, -1.25, 0.9), 8.6, (1000, 1000))
    # Keep the top-positive corner. Cut stubs only in this temporary render scene.
    names = {"X receiver Y+1 Z+1", "Y dovetail X+1 Z+1", "Z keyed post X+1 Y+1"}
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        if obj.name not in names:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        crop = box("Detail crop", (1.15, 1.15, 1.45), (2.6, 2.6, 2.6))
        boolean(obj, crop, "INTERSECT")
    bpy.data.objects["Y dovetail X+1 Z+1"].location.z -= 0.62
    post = bpy.data.objects["Z keyed post X+1 Y+1"]
    post.location += Vector((0.60, 0.50, -0.90))
    render_view(output / "joint-detail.png", (2.08, 2.15, 1.69), (-1.2, -1.6, -1.0), 3.9, (1250, 1050))


if __name__ == "__main__":
    main()
