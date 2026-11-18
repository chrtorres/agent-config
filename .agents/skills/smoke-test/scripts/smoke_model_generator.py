"""Generate one synthetic Blender model and its rendered/GLB review artifacts."""

import argparse
import os
import sys

import bpy
from mathutils import Vector


def aim(obj):
    obj.rotation_euler = (Vector((0, 0, 0)) - obj.location).to_track_quat("-Z", "Y").to_euler()


def create_material():
    material = bpy.data.materials.new("Smoke_Test_Material")
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (0.12, 0.42, 0.85, 1.0)
    node.inputs["Roughness"].default_value = 0.28
    return material


def create_shape(shape, material):
    if shape == "cube":
        bpy.ops.mesh.primitive_cube_add(size=100)
    elif shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=50)
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=42, depth=100)
    elif shape == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=50, radius2=18, depth=100)
    elif shape == "torus":
        bpy.ops.mesh.primitive_torus_add(major_radius=34, minor_radius=13, major_segments=64, minor_segments=20)
    elif shape == "ico":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=50)
    else:
        raise ValueError(f"Unsupported smoke-test shape: {shape}")
    obj = bpy.context.object
    obj.name = f"Smoke_{shape}"
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = shape not in {"cube", "cylinder", "cone"}


def parse_blender_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shape", required=True, choices=("cube", "sphere", "cylinder", "cone", "torus", "ico"))
    parser.add_argument("--style", required=True, choices=("soft", "left", "right", "rim", "top", "cross"))
    parser.add_argument("--output", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


args = parse_blender_args()
output = os.path.abspath(args.output)
os.makedirs(output, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
create_shape(args.shape, create_material())

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 500
scene.render.resolution_y = 500
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(output, "preview.png")
scene.world.color = (0.03, 0.03, 0.03)
scene.view_settings.look = "AgX - Medium High Contrast"

light_settings = {
    "soft": ((150, -180, 220), 1200, 160),
    "left": ((-180, -120, 160), 1800, 90),
    "right": ((180, -100, 130), 1800, 90),
    "rim": ((0, 180, 210), 2200, 70),
    "top": ((0, -80, 260), 2000, 55),
    "cross": ((-160, -160, 200), 1500, 70),
}
location, energy, size = light_settings[args.style]
bpy.ops.object.light_add(type="AREA", location=location)
key = bpy.context.object
key.data.energy = energy
key.data.size = size
aim(key)
if args.style in {"cross", "rim"}:
    bpy.ops.object.light_add(type="AREA", location=(160, 120, 90))
    fill = bpy.context.object
    fill.data.energy = 900
    fill.data.size = 80
    aim(fill)

bpy.ops.object.camera_add(location=(175, -205, 150))
camera = bpy.context.object
camera.data.lens = 58
scene.camera = camera
aim(camera)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output, "model.blend"))
bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(output, "model.glb"), export_format="GLB", use_selection=False)
