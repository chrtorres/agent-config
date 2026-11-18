"""Create a beveled open cube frame with Blender."""
import argparse
import sys
from pathlib import Path

import bpy


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--outer-size", type=float, default=5.0)
    parser.add_argument("--beam-size", type=float, default=0.5)
    parser.add_argument("--bevel", type=float, default=0.06)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def add_beam(name, location, dimensions, bevel):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new(name="Edge bevel", type="BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def build_frame(outer_size, beam_size, bevel):
    clear_scene()
    half = (outer_size - beam_size) / 2.0
    beams = []
    for y in (-half, half):
        for z in (-half, half):
            beams.append(add_beam(f"Beam_X_{len(beams) + 1:02d}", (0, y, z), (outer_size, beam_size, beam_size), bevel))
    for x in (-half, half):
        for z in (-half, half):
            beams.append(add_beam(f"Beam_Y_{len(beams) + 1:02d}", (x, 0, z), (beam_size, outer_size, beam_size), bevel))
    for x in (-half, half):
        for y in (-half, half):
            beams.append(add_beam(f"Beam_Z_{len(beams) + 1:02d}", (x, y, 0), (beam_size, beam_size, outer_size), bevel))

    bpy.ops.object.select_all(action="DESELECT")
    for beam in beams:
        beam.select_set(True)
    bpy.context.view_layer.objects.active = beams[0]
    bpy.ops.object.join()
    frame = bpy.context.object
    frame.name = "Box_Frame"
    frame["outer_size"] = outer_size
    frame["beam_size"] = beam_size
    frame["beam_count"] = len(beams)
    return frame


def main():
    args = arguments()
    if args.outer_size <= args.beam_size or args.beam_size <= 0 or args.bevel < 0:
        raise ValueError("Require outer-size > beam-size > 0 and bevel >= 0")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = build_frame(args.outer_size, args.beam_size, args.bevel)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["model_description"] = "Open cube box frame"
    scene["outer_size"] = args.outer_size
    scene["beam_size"] = args.beam_size
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "box-frame.blend"))
    print("MODEL_CREATED", frame.name, tuple(round(value, 4) for value in frame.dimensions), len(frame.data.vertices))


if __name__ == "__main__":
    main()
