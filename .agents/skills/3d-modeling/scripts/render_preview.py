"""Render a review preview from a generated Blender file."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main():
    args = arguments()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend))
    target = Vector((0, 0, 0))
    bpy.ops.object.camera_add(location=(8.8, -8.8, 7.0))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 52

    for location, energy, size in [((4, -4, 8), 950, 5), ((-5, -1, 3), 500, 4), ((0, 5, 5), 700, 3)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.size = size
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output)
    scene.world.color = (0.035, 0.045, 0.06)
    bpy.ops.render.render(write_still=True)
    print("PREVIEW_RENDERED", args.output)


if __name__ == "__main__":
    main()
