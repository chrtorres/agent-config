"""Check part topology, assembled fit, and straight-line assembly poses."""
from itertools import combinations

import bmesh
import bpy
from mathutils import Vector

EPS = 1e-6
VOLUME_TOLERANCE = 2e-7


def solid_check(obj):
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        assert len(bm.faces) and all(edge.is_manifold and edge.is_contiguous for edge in bm.edges), obj.name
        seen = {next(iter(bm.verts))}
        pending = list(seen)
        while pending:
            current = pending.pop()
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        assert len(seen) == len(bm.verts), f"Disconnected shell: {obj.name}"
        assert bm.calc_volume(signed=True) > 0, f"Nonpositive volume: {obj.name}"
    finally:
        bm.free()


def bounds(obj):
    points = [obj.matrix_world @ Vector(point) for point in obj.bound_box]
    return [(min(point[axis] for point in points), max(point[axis] for point in points))
            for axis in range(3)]


def overlap(first, second):
    for (lo, hi), (other_lo, other_hi) in zip(bounds(first), bounds(second)):
        if min(hi, other_hi) - max(lo, other_lo) < EPS:
            return 0.0
    modifier = first.modifiers.new("Verification intersection", "BOOLEAN")
    modifier.solver = "EXACT"
    modifier.operation = "INTERSECT"
    modifier.object = second
    bm = bmesh.new()
    try:
        evaluated = first.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bm.from_mesh(evaluated.data)
        return abs(bm.calc_volume(signed=True))
    finally:
        bm.free()
        first.modifiers.remove(modifier)


def check_motion(label, moving, stationary, direction, travel, steps):
    start = [obj.location.copy() for obj in moving]
    tests = 0
    try:
        for sample in range(steps + 1):
            offset = Vector(direction) * (travel * (1 - sample / steps))
            for obj, origin in zip(moving, start):
                obj.location = origin + offset
            bpy.context.view_layer.update()
            for first in moving:
                for second in stationary:
                    volume = overlap(first, second)
                    assert volume < VOLUME_TOLERANCE, (label, sample, first.name, second.name, volume)
                    tests += 1
    finally:
        for obj, origin in zip(moving, start):
            obj.location = origin
        bpy.context.view_layer.update()
    print(f"{label}: {steps + 1} poses, {tests} pair checks")


def main():
    parts = list(bpy.context.scene.objects)
    receivers = [obj for obj in parts if obj["role"] == "X receiver"]
    tails = [obj for obj in parts if obj["role"] == "Y dovetail"]
    posts = [obj for obj in parts if obj["role"] == "Z keyed post"]
    assert len(parts) == 12 and len(receivers) == len(tails) == len(posts) == 4
    for obj in parts:
        solid_check(obj)
    extents = [bounds(obj) for obj in parts]
    axes = list(zip(*extents))
    envelope = [max(interval[1] for interval in axis) - min(interval[0] for interval in axis)
                for axis in axes]
    assert all(abs(size - 5) < EPS for size in envelope), envelope
    for first, second in combinations(parts, 2):
        volume = overlap(first, second)
        assert volume < VOLUME_TOLERANCE, (first.name, second.name, volume)
    print(f"12 connected manifold rail solids, envelope {envelope}, 66 assembled pair checks")

    for z in (-1, 1):
        ring_receivers = [obj for obj in receivers if obj["fixed_signs"][1] == z]
        ring_tails = [obj for obj in tails if obj["fixed_signs"][1] == z]
        for index, tail in enumerate(ring_tails):
            check_motion(f"Ring {z:+d}, Y rail {index + 1}", [tail],
                         ring_receivers + ring_tails[:index], (0, 0, -z), 0.55, 22)
    top_ring = [obj for obj in receivers + tails if obj["fixed_signs"][1] == 1]
    bottom_ring = [obj for obj in receivers + tails if obj["fixed_signs"][1] == -1]
    check_motion("Posts into bottom ring", posts, bottom_ring, (0, 0, 1), 0.24, 12)
    check_motion("Top ring onto posts", top_ring, posts + bottom_ring, (0, 0, 1), 0.24, 12)

    # Pull one dovetail rail away from its receiver along its length without lifting.
    tail = next(obj for obj in tails if list(obj["fixed_signs"]) == [1, -1])
    receiver = next(obj for obj in receivers if list(obj["fixed_signs"]) == [1, -1])
    installed = tail.location.copy()
    tail.location.y -= 0.23
    bpy.context.view_layer.update()
    engagement = overlap(tail, receiver)
    assert engagement > 100 * VOLUME_TOLERANCE, engagement
    print(f"Dovetail undercut blocks straight rail withdrawal: {engagement:.6f} cubic units of interference")
    tail.location = installed
    tail.location.z += 0.06
    bpy.context.view_layer.update()
    interference = max(overlap(tail, post) for post in posts)
    assert interference > 100 * VOLUME_TOLERANCE, interference
    print(f"Seated posts block the dovetail slide direction: {interference:.6f} cubic units of interference")


if __name__ == "__main__":
    main()
