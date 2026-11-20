"""Render a synthetic animated scene to numbered frames with Blender Python."""

from argparse import ArgumentParser
from pathlib import Path
import sys
from math import sin, tau

import bpy
from mathutils import Vector


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1)
    cube = bpy.context.object
    cube.color = (0.9, 0.35, 0.05, 1)
    bpy.ops.object.camera_add(location=(4, -6, 4))
    camera = bpy.context.object
    camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 320, 240
    scene.render.resolution_percentage = 100
    scene.render.fps = 12
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.color_type = "OBJECT"
    for index in range(12):
        phase = tau * index / 12
        scene.frame_set(index + 1)
        cube.location = Vector((1.2 * sin(phase), 0, 0))
        cube.rotation_euler = (phase / 2, phase / 3, phase)
        scene.render.filepath = str((args.output / f"frame-{index:04d}.png").resolve())
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
