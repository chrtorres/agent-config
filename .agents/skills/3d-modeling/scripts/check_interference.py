"""Report mesh-level intersections between assembled parts in a .blend file.

Run inside Blender:
    blender -b <model.blend> --python-exit-code 1 --python check_interference.py -- \
        [--allow allowlist.json] [--poses poses.json] [--report out.json] [--strict]

Each top-level mesh object is one part. Pairs whose bounding boxes overlap are
tested with BVH triangle overlap in world space. The allowlist names pairs that
intersect by design (for example, a part seated in a molded pocket) with a reason.
With --strict, any intersecting pair missing from the allowlist exits non-zero.

--poses names joint poses to sweep. Each pose moves named parts about their object
origin (which sits on the joint axis) by a local rotation in degrees and/or a
translation in metres, then re-tests every pair that involves a moved part. A move may
name "about": <part> to rotate about another part's origin (e.g. a caster wheel about
its swivel). Objects carrying the --skip-property custom property (default
"review_guide") are viewer guides, not parts, and are excluded.
"""

import argparse
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import bpy
from mathutils import Euler, Matrix
from mathutils.bvhtree import BVHTree


def world_tree(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    vertices = [obj.matrix_world @ v.co for v in data.vertices]
    polygons = [tuple(p.vertices) for p in data.polygons]
    evaluated.to_mesh_clear()
    lo = [min(v[i] for v in vertices) for i in range(3)]
    hi = [max(v[i] for v in vertices) for i in range(3)]
    return BVHTree.FromPolygons(vertices, polygons), (lo, hi), vertices, polygons


def boxes_touch(a, b, pad=1e-6):
    return all(a[0][i] <= b[1][i] + pad and b[0][i] <= a[1][i] + pad for i in range(3))


def find_pairs(parts, allowed, depsgraph, scale, only=None):
    trees = {obj.name: world_tree(obj, depsgraph) for obj in parts}
    findings = []
    for a, b in combinations(sorted(trees), 2):
        if only and a not in only and b not in only:
            continue
        (tree_a, box_a, verts_a, polys_a), (tree_b, box_b, _vb, _pb) = trees[a], trees[b]
        if not boxes_touch(box_a, box_b):
            continue
        hits = tree_a.overlap(tree_b)
        if hits:
            reason = allowed.get(frozenset((a, b)))
            # Region of the intersecting faces of the first part, in scene millimetres.
            points = [verts_a[i] for hit in hits for i in polys_a[hit[0]]]
            region = [[round(min(p[k] for p in points) * scale, 2) for k in range(3)],
                      [round(max(p[k] for p in points) * scale, 2) for k in range(3)]]
            findings.append({"pair": [a, b], "triangle_pairs": len(hits), "region_mm": region,
                             "allowed": reason is not None, "reason": reason})
    return findings


def print_findings(findings):
    for f in findings:
        flag = "ALLOWED" if f["allowed"] else "UNEXPECTED"
        print(f"{flag:10s} {f['triangle_pairs']:6d}  {f['pair'][0]}  <->  {f['pair'][1]}"
              + f"  region {f['region_mm']}" + (f"  ({f['reason']})" if f["reason"] else ""))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--poses", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--skip-property", default="review_guide",
                        help="custom property marking viewer-only guide objects to exclude")
    args = parser.parse_args(argv)
    allowed = {}
    if args.allow:
        for entry in json.loads(args.allow.read_text()):
            allowed[frozenset(entry["pair"])] = entry["reason"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    parts = [obj for obj in bpy.context.scene.objects
             if obj.type == "MESH" and obj.parent is None and obj.visible_get()
             and not obj.get(args.skip_property)]
    scale = 1000.0 if bpy.context.scene.unit_settings.length_unit == "MILLIMETERS" else 1.0
    findings = find_pairs(parts, allowed, depsgraph, scale)
    unexpected = [f for f in findings if not f["allowed"]]
    stale = [sorted(pair) for pair in allowed if not any(frozenset(f["pair"]) == pair for f in findings)]
    print(f"parts={len(parts)} intersecting_pairs={len(findings)} unexpected={len(unexpected)} "
          f"stale_allowlist={len(stale)}")
    print_findings(findings)
    for pair in stale:
        print(f"STALE      allowlisted pair no longer intersects: {pair}")
    pose_results = []
    if args.poses:
        byname = {obj.name: obj for obj in parts}
        for pose in json.loads(args.poses.read_text()):
            saved = {}
            for move in pose["moves"]:
                obj = byname[move["node"]]
                saved[obj.name] = obj.matrix_world.copy()
                rotation = Euler([math.radians(v) for v in move.get("rotate_deg", (0, 0, 0))]).to_matrix().to_4x4()
                offset = Matrix.Translation(move.get("translate_m", (0, 0, 0)))
                pivot = byname[move["about"]] if "about" in move else obj
                origin = saved.get(pivot.name, pivot.matrix_world).to_translation()
                obj.matrix_world = (offset @ Matrix.Translation(origin) @ rotation
                                    @ Matrix.Translation(-origin) @ obj.matrix_world)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            moved = set(saved)
            posed = find_pairs(parts, allowed, depsgraph, scale, only=moved)
            bad = [f for f in posed if not f["allowed"]]
            print(f"POSE {pose['name']}: moved={sorted(moved)} intersecting={len(posed)} unexpected={len(bad)}")
            print_findings(posed)
            unexpected += bad
            pose_results.append({"pose": pose["name"], "findings": posed})
            for name, matrix in saved.items():
                byname[name].matrix_world = matrix
            bpy.context.view_layer.update()
    if args.report:
        args.report.write_text(json.dumps({"parts": len(parts), "findings": findings,
                                           "stale_allowlist": stale, "poses": pose_results}, indent=2) + "\n")
    if args.strict and unexpected:
        sys.exit(1)


if __name__ == "__main__":
    main()
