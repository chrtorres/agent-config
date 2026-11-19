"""Sample feature vertices against a named, closed reference mesh in Blender."""
import argparse
import bmesh
import bpy
import json
from mathutils.bvhtree import BVHTree
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--envelope", required=True)
parser.add_argument("--feature", action="append", required=True)
parser.add_argument("--mm-per-unit", type=float, default=1000)
parser.add_argument("--tolerance-mm", type=float, required=True)
parser.add_argument("--stride", type=int, default=1)
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
if args.mm_per_unit <= 0 or args.tolerance_mm < 0 or args.stride < 1:
    parser.error("unit scale and stride must be positive and tolerance must be nonnegative")
reference = bpy.data.objects[args.envelope]
mesh = reference.data
bm = bmesh.new()
bm.from_mesh(mesh)
if reference.matrix_world.to_3x3().determinant() <= 0 or bm.calc_volume(signed=True) <= 0 or not all(
    edge.is_manifold and edge.is_contiguous for edge in bm.edges
):
    parser.error("envelope must be closed, consistently outward oriented and positively transformed")
bm.free()
mesh.calc_loop_triangles()
tree = BVHTree.FromPolygons([reference.matrix_world @ v.co for v in mesh.vertices],
                            [tuple(tri.vertices) for tri in mesh.loop_triangles], all_triangles=True)
result = {}
for name in args.feature:
    obj = bpy.data.objects[name]
    indices = range(0, len(obj.data.vertices), args.stride)
    outside = []
    for index in indices:
        point = obj.matrix_world @ obj.data.vertices[index].co
        nearest, normal, _, distance = tree.find_nearest(point)
        # Nearest oriented-surface sign is a local fit check, especially near sharp edges.
        if (point-nearest).dot(normal) > 0 and distance*args.mm_per_unit > args.tolerance_mm:
            outside.append(distance*args.mm_per_unit)
    result[name] = {"samples": len(indices), "outside_tolerance":len(outside),
                    "maximum_flagged_mm":max(outside, default=0)}
print(json.dumps({"tolerance_mm":args.tolerance_mm, "features":result}, indent=2), flush=True)
if any(row["outside_tolerance"] for row in result.values()):
    raise RuntimeError("reference envelope tolerance exceeded")
