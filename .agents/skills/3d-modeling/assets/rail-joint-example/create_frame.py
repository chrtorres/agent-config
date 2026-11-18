"""Create the twelve-rail dovetail fixture in its assembled pose."""
import argparse
from itertools import product
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

OUTER = 5.0
WIDTH = 0.50
HALF = OUTER / 2
INNER = HALF - WIDTH
CLEARANCE = 0.020
SHOULDER_GAP = 0.012
GROOVE_FLOOR = 0.12
TAIL_BOTTOM = GROOVE_FLOOR + CLEARANCE
TAIL_TIP = 0.12
TAIL_HEAD = 0.34
TAIL_NECK = 0.26
POST_KEY = 0.17
POST_DEPTH = 0.17


def prism(name, outline, low, high, transform=lambda xyz: xyz):
    count = len(outline)
    vertices = [transform((x, y, z)) for z in (low, high) for x, y in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def box(name, low, high):
    return prism(name, rect(low[0], high[0], low[1], high[1]), low[2], high[2])


def boolean(target, tool, operation):
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(operation.title(), "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def local_corner(signs):
    # Local coordinates measure inward from the three outside faces.
    return lambda point: tuple(sign * (HALF - value) for sign, value in zip(signs, point))


def span(sign):
    return sorted((sign * INNER, sign * HALF))


def dovetail(t0, t1, w0, w1):
    center = WIDTH / 2
    return [(center - w0 / 2, t0), (center + w0 / 2, t0),
            (center + w1 / 2, t1), (center - w1 / 2, t1)]


def key_outline(size):
    low = (WIDTH - size) / 2
    return rect(low, low + size, low, low + size)


def mortise(rail, transform):
    cutter = prism("Mortise cutter", key_outline(POST_KEY + 2 * CLEARANCE),
                   WIDTH - POST_DEPTH - CLEARANCE, WIDTH + 0.05, transform)
    boolean(rail, cutter, "DIFFERENCE")


def tag(rail, role, signs, color):
    rail["role"] = role
    rail["fixed_signs"] = signs
    material = bpy.data.materials.get(role) or bpy.data.materials.new(role)
    material.diffuse_color = (*color, 1)
    rail.data.materials.append(material)
    bpy.context.view_layer.objects.active = rail
    rail.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    rail.select_set(False)
    return rail


def receiver(y, z):
    y0, y1 = span(y)
    z0, z1 = span(z)
    rail = box(f"X receiver Y{y:+d} Z{z:+d}", (-HALF, y0, z0), (HALF, y1, z1))
    for x in (-1, 1):
        transform = local_corner((x, y, z))
        profile = dovetail(TAIL_TIP - CLEARANCE, WIDTH + 0.04,
                           TAIL_HEAD + 2 * CLEARANCE, TAIL_NECK + 2 * CLEARANCE)
        cutter = prism("Dovetail cutter", profile, GROOVE_FLOOR, WIDTH + 0.05, transform)
        boolean(rail, cutter, "DIFFERENCE")
        mortise(rail, transform)
    return tag(rail, "X receiver", (y, z), (0.11, 0.42, 0.66))


def tail_rail(x, z):
    x0, x1 = span(x)
    z0, z1 = span(z)
    end = INNER - SHOULDER_GAP
    rail = box(f"Y dovetail X{x:+d} Z{z:+d}", (x0, -end, z0), (x1, end, z1))
    for y in (-1, 1):
        transform = local_corner((x, y, z))
        profile = dovetail(TAIL_TIP, WIDTH + 0.06, TAIL_HEAD, TAIL_NECK)
        tail = prism("Integral dovetail", profile, TAIL_BOTTOM, WIDTH, transform)
        boolean(rail, tail, "UNION")
        mortise(rail, transform)
    return tag(rail, "Y dovetail", (x, z), (0.89, 0.49, 0.16))


def post(x, y):
    x0, x1 = span(x)
    y0, y1 = span(y)
    rail = box(f"Z keyed post X{x:+d} Y{y:+d}", (x0, y0, -INNER), (x1, y1, INNER))
    for z in (-1, 1):
        tenon = prism("Integral key", key_outline(POST_KEY),
                      WIDTH - POST_DEPTH, WIDTH + 0.05, local_corner((x, y, z)))
        boolean(rail, tenon, "UNION")
    return tag(rail, "Z keyed post", (x, y), (0.68, 0.75, 0.82))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    for first, second in product((-1, 1), repeat=2):
        receiver(first, second)
        tail_rail(first, second)
        post(first, second)
    scene = bpy.context.scene
    scene["review_state"] = "Draft — awaiting preview approval"
    scene["outer_size_in_model_units"] = OUTER
    scene["rail_width_in_model_units"] = WIDTH
    scene["fit_allowance_in_model_units"] = CLEARANCE
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                viewport = area.spaces.active
                viewport.shading.color_type = "MATERIAL"
                viewport.region_3d.view_distance = 13
                viewport.region_3d.view_rotation = Vector((1, -1.4, 1)).to_track_quat("Z", "Y")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output))


if __name__ == "__main__":
    main()
