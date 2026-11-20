"""Measure directional cover clearance on an imported GLB in Blender."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def mesh_geometry(name, depsgraph, reference):
    obj = bpy.data.objects[name].evaluated_get(depsgraph)
    if obj.type != "MESH":
        raise ValueError(f"{name} must name a mesh")
    transform = reference @ obj.matrix_world
    return ([transform @ v.co for v in obj.data.vertices],
            [tuple(face.vertices) for face in obj.data.polygons])


def measure(contract):
    axis = Vector(contract["view_direction"])
    margin = float(contract["min_clearance_m"])
    minimum = contract["min_samples"]
    if len(axis) != 3 or not all(math.isfinite(v) for v in axis) or not axis.length:
        raise ValueError("Expected a finite, nonzero three-component view direction")
    if not math.isfinite(margin) or margin < 0 or type(minimum) is not int or minimum < 1:
        raise ValueError("Expected a nonnegative clearance and a positive sample count")
    limits = contract["sample_bounds"]
    if (len(limits) != 3 or any(len(pair) != 2 or
            not all(math.isfinite(v) for v in pair) or pair[0] > pair[1] for pair in limits)):
        raise ValueError("Expected three finite, ordered sample intervals")
    axis.normalize()
    graph = bpy.context.evaluated_depsgraph_get()
    reference = bpy.data.objects[contract["frame"]].evaluated_get(graph).matrix_world.inverted()
    samples, _ = mesh_geometry(contract["sample_mesh"], graph, reference)
    samples = [point for point in samples
               if all(lo <= value <= hi for value, (lo, hi) in zip(point, limits))]
    vertices, faces = [], []
    for name in contract["cover_meshes"]:
        points, polygons = mesh_geometry(name, graph, reference)
        faces.extend(tuple(i + len(vertices) for i in polygon) for polygon in polygons)
        vertices.extend(points)
    if not vertices or not faces:
        raise ValueError("Expected at least one cover mesh with faces")

    surface = BVHTree.FromPolygons(vertices, faces)
    cover_extent = max(point.dot(axis) for point in vertices)
    clearances = []
    for point in samples:
        offset = max(cover_extent - point.dot(axis), 0) + .001
        hit, _, _, _ = surface.ray_cast(point + axis * offset, -axis)
        if hit is not None:
            clearances.append((hit - point).dot(axis))
    worst = min(clearances, default=None)
    return {"samples": len(samples), "rays_without_cover": len(samples) - len(clearances),
            "min_clearance_m": worst, "required_clearance_m": margin,
            "passed": len(samples) >= minimum and len(samples) == len(clearances)
            and worst is not None and worst >= margin}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    data = args.asset.read_bytes()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.asset.resolve()))
    result = measure(json.loads(args.contract.read_text(encoding="utf-8")))
    print(json.dumps({"asset_sha256": hashlib.sha256(data).hexdigest(), **result}, indent=2))
    if not result["passed"]:
        raise RuntimeError("Directional fit failed")


if __name__ == "__main__":
    main()
