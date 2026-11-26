"""Reusable Blender scaffolding for rendering assembly install-guide views.

Run headless:  blender -b --python render_install_views.py -- <config.json>

The caller writes a JSON config that describes the assembly (STL paths,
positions, materials, camera views, labels).  This module provides the
camera, lighting, material, label, and render helpers so the caller only
supplies geometry layout.

Requires: Blender 4.x with EEVEE.
"""
import json
import math
import os
import sys

try:
    import bpy
    from mathutils import Euler, Vector
except ImportError:
    raise SystemExit("Run inside Blender: blender -b --python render_install_views.py -- config.json")


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def clear_scene():
    """Remove all objects, datablocks and worlds so the scene is blank."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for pool in (bpy.data.materials, bpy.data.meshes, bpy.data.cameras,
                 bpy.data.lights, bpy.data.curves, bpy.data.worlds):
        for item in list(pool):
            pool.remove(item)


def master_collection():
    return bpy.context.scene.collection


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def make_material(name, rgba, metallic=0.0, roughness=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return m


# ---------------------------------------------------------------------------
# STL import and placement
# ---------------------------------------------------------------------------

def import_stl(filepath, name):
    bpy.ops.wm.stl_import(filepath=filepath)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    return ob


def world_bounds(ob):
    bpy.context.view_layer.update()
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs, ys, zs = zip(*[(v.x, v.y, v.z) for v in bb])
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def flip_z(ob, total_depth):
    """Flip an object 180 deg around X (for parts printed upside down)."""
    ob.rotation_euler = Euler((math.pi, 0, 0))
    bpy.context.view_layer.update()
    ob.location.z += total_depth
    bpy.context.view_layer.update()


def snap_to_origin(ob, grid_x, grid_y):
    """Translate so the object's min-X/Y corner aligns to (grid_x, grid_y, 0)."""
    bpy.context.view_layer.update()
    bx0, by0, bz0, _, _, _ = world_bounds(ob)
    ob.location.x += grid_x - bx0
    ob.location.y += grid_y - by0
    ob.location.z += -bz0
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# 3D text labels
# ---------------------------------------------------------------------------

def add_label(text, location, size=8, rgba=(0.1, 0.1, 0.1, 1)):
    fc = bpy.data.curves.new(text, 'FONT')
    fc.body = text
    fc.size = size
    fc.align_x = 'CENTER'
    fc.align_y = 'CENTER'
    fc.extrude = 0.3
    ob = bpy.data.objects.new(text, fc)
    master_collection().objects.link(ob)
    ob.location = Vector(location)
    ob.data.materials.append(make_material(f'lbl_{text}', rgba))
    return ob


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

def ortho_camera(name, target, distance, azimuth_deg, elevation_deg, ortho_scale):
    """Place an orthographic camera looking at *target* from the given angles.

    Uses a TRACK_TO constraint for reliable aiming — avoids manual Euler errors.
    """
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    dx = distance * math.cos(el) * math.sin(az)
    dy = -distance * math.cos(el) * math.cos(az)
    dz = distance * math.sin(el)
    loc = (target[0] + dx, target[1] + dy, target[2] + dz)

    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO'
    cd.ortho_scale = ortho_scale
    ob = bpy.data.objects.new(name, cd)
    master_collection().objects.link(ob)
    ob.location = Vector(loc)

    emp = bpy.data.objects.new(f'{name}_target', None)
    master_collection().objects.link(emp)
    emp.location = Vector(target)

    tc = ob.constraints.new('TRACK_TO')
    tc.target = emp
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    bpy.context.view_layer.update()
    return ob


# ---------------------------------------------------------------------------
# Lighting and render setup
# ---------------------------------------------------------------------------

def standard_lighting():
    """Two-sun + ambient setup that reads clearly in documentation renders."""
    key = bpy.data.lights.new('Key', 'SUN')
    key.energy = 4.0
    key.color = (1.0, 0.98, 0.95)
    ko = bpy.data.objects.new('Key', key)
    master_collection().objects.link(ko)
    ko.rotation_euler = Euler((math.radians(50), math.radians(10), math.radians(-30)))

    fill = bpy.data.lights.new('Fill', 'SUN')
    fill.energy = 2.0
    fill.color = (0.90, 0.93, 1.0)
    fo = bpy.data.objects.new('Fill', fill)
    master_collection().objects.link(fo)
    fo.rotation_euler = Euler((math.radians(60), math.radians(-20), math.radians(150)))

    w = bpy.data.worlds.new('DocWorld')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.91, 0.89, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    bpy.context.scene.world = w


def configure_render(width=1600, height=1200, samples=64, transparent=False):
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE_NEXT'
    s.render.resolution_x = width
    s.render.resolution_y = height
    s.render.resolution_percentage = 100
    s.render.film_transparent = transparent
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.eevee.taa_render_samples = samples


def render_view(camera, output_path):
    bpy.context.scene.camera = camera
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f'Saved {os.path.basename(output_path)}')


# ---------------------------------------------------------------------------
# CLI entry point (optional — the caller can also import functions directly)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    argv = sys.argv
    if '--' in argv:
        args = argv[argv.index('--') + 1:]
    else:
        args = []
    if not args:
        print("Usage: blender -b --python render_install_views.py -- config.json")
        print("This module is typically imported by a project-specific render script.")
        sys.exit(0)

    cfg_path = args[0]
    with open(cfg_path) as f:
        cfg = json.load(f)
    print(f"Loaded config: {cfg_path}")
    print("Config-driven batch rendering is project-specific — see assembly-install-guide.md")
