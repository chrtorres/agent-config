"""Measure a character's clothed silhouette per height for a runtime cloth collider.

Run inside Blender:

    blender -b --python-exit-code 1 --python measure_body_profile.py -- <model.glb> \
        [--root <root-node>] [--exclude <node> ...] [--step 0.05] [--json <out.json>]

Prints rows of [height, back depth, half-width, front depth] in model units (the root
node's scale is divided out), the format the cloth collider example's makeProfile() takes.
Blender's -Y is forward, so "back" is the largest +Y and "front" the largest -Y.

Exclude nodes that move or stand off the body (arms, hats, scabbards, swinging panels);
their whole subtree is skipped. Lofted garments often have rings several centimetres
apart, so edges spanning height bands are sampled as well as vertices: vertex-only
sampling leaves bands between rings empty and the collider falls through there.
"""
import argparse
import json
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument('glb')
parser.add_argument('--root', help='node whose scale converts world to model units')
parser.add_argument('--exclude', nargs='*', default=[])
parser.add_argument('--step', type=float, default=.05)
parser.add_argument('--top', type=float, default=None, help='highest model height to sample')
parser.add_argument('--json')
args = parser.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args.glb)
scale = bpy.data.objects[args.root].matrix_world.to_scale().x if args.root else 1.0
skip = set(args.exclude)


def kept(obj):
    while obj:
        if obj.name in skip:
            return False
        obj = obj.parent
    return True


points = []
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not kept(obj):
        continue
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    points += world
    for edge in obj.data.edges:
        a, b = world[edge.vertices[0]], world[edge.vertices[1]]
        if abs(a.z - b.z) > args.step * .4:
            points += [a.lerp(b, t / 12) for t in range(1, 12)]

if not points:
    sys.exit('No mesh vertices remain after exclusions')
top = args.top if args.top is not None else max(p.z for p in points) / scale
rows = []
k = 1
while k * args.step <= top + 1e-9:
    h = k * args.step
    band = [p for p in points if abs(p.z / scale - h) <= args.step / 2]
    if band:
        rows.append([round(h, 3), round(max(max(p.y for p in band), 0) / scale, 3),
                     round(max(abs(p.x) for p in band) / scale, 3),
                     round(max(max(-p.y for p in band), 0) / scale, 3)])
    k += 1
print('PROFILE ' + json.dumps(rows))
if args.json:
    with open(args.json, 'w') as handle:
        json.dump({'scale': scale, 'excluded': sorted(skip), 'rows': rows}, handle, indent=2)
