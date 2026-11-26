# Assembly install guide — PDF from printed parts

When a 3D-printed project reaches the assembly stage — parts are printed and need to be
bolted, snapped, or glued together — generate a visual PDF install guide alongside the
project files. The guide is a deliverable: it travels with the parts and survives the
conversation.

## When to produce a guide

Create an install guide when:
- A project has **multiple printed parts** that assemble with hardware (bolts, nuts, inserts)
- The assembly has a **specific orientation, order, or bolt pattern** that is not obvious
  from the parts alone
- The user is about to **physically assemble** printed parts and asks how they go together

Do not generate a guide for single-part prints or trivial snap-fits unless the user asks.

## What the guide contains

Each guide is a multi-page PDF with **rendered images from the actual STL/Blend geometry**,
not hand-drawn diagrams or text-only instructions. Pages typically include:

1. **Cover / overview** — 3/4 hero render of the assembled result, hardware bill of
   materials, part identity table (which parts are flipped, which are as-built)
2. **Top and bottom views** — orthographic renders showing the nut side vs. screw side,
   with labels identifying which holes are hex pockets and which are counterbores
3. **Cross-section / bolt orientation** — schematic showing how the fastener passes through
   the joint, color-coded (e.g. gold = nut, blue = screw head)
4. **Exploded view** — parts pulled apart to show the interlock mechanism (half-laps,
   dovetails, tongue-and-groove)
5. **Step-by-step assembly** — numbered steps with the tile/seam map showing bolt positions
6. **Inspection checklist** — what to check after assembly (flush seams, no rocking, etc.)

## Rendering procedure

Use Blender headless (`blender -b --python <script>`) to render from the project's own
STL files. The render script:

1. Imports each STL and positions it in the frame coordinate system (un-flipping parts that
   were printed upside down)
2. Assigns distinct materials to visually distinguish parts (lighter for one tongue type,
   darker for the other; color-coded fastener representations)
3. Adds 3D text labels directly in the scene (part names, annotations)
4. Uses orthographic cameras with `TRACK_TO` constraints pointed at the assembly centre
5. Renders with EEVEE for speed (64 samples is sufficient for documentation)
6. Outputs PNG images to a temporary directory

For cross-section / bolt-orientation diagrams, build schematic geometry from primitives
(cubes for tile halves, cylinders for bolt shafts, hex cylinders for nuts) rather than
bisecting the actual STL — it reads more clearly at documentation scale.

**Camera tips:**
- Use `cam_at_target()` with azimuth/elevation angles and a `TRACK_TO` constraint rather
  than computing Euler rotations by hand — Euler angles for oblique ortho views are error-prone
- Ortho scale should be ~1.3× the assembly's widest dimension
- Non-transparent background (solid light grey) reads better in PDFs than transparent PNG

## PDF composition

Use `reportlab` (install if needed: `pip install reportlab`). The PDF builder:

1. Reads the rendered PNGs and fits each into a page region preserving aspect ratio
2. Uses `canvas.Canvas` for precise placement of images, text blocks, numbered steps,
   color-coded callout boxes, and drawn diagrams (tile maps, bolt-position dots)
3. Saves the PDF **inside the project's version directory** alongside the STL/gcode files

**Layout guidelines:**
- Letter size (8.5 × 11 in), 0.6 in margins
- Hardware BOM in a tinted rounded-rect box
- Steps use numbered accent-colored circles
- Captions under each image in italic
- Inspection checklists use bullet points
- Raft/tolerance reminders in a warning-colored box at the end

## File placement

```
<project>/version-NNN/sled/
├── stl/
├── gcode/
├── profiles/
├── build_sled.py
└── v021_2x2_bolt_guide.pdf    ← install guide lives here
```

The guide file name should identify the assembly scope (e.g. `v021_2x2_bolt_guide.pdf`,
`v021_full_frame_guide.pdf`). One guide per assembly milestone.

## Adapting to other projects

The render and PDF scripts are project-specific (they know the tile grid, bolt pattern,
and member layout). To adapt for a new project:

1. **Read the project's build script** to find the parametric dimensions, bolt positions,
   seam locations, and part naming convention
2. **Write a render script** that imports the project's STLs and positions them using
   those same parameters
3. **Write a PDF script** that composes the rendered images with project-specific hardware
   lists, step descriptions, and inspection criteria

The helper scripts in this skill ([render_install_views.py](../scripts/render_install_views.py)
and [build_install_pdf.py](../scripts/build_install_pdf.py)) provide the reusable
scaffolding — camera setup, material creation, PDF page layout — so a project-specific
guide only needs to supply the geometry positions and text content.

## What the guide does NOT replace

- The project's README.md (which covers the full print order, all tiles, rebuild commands)
- The HANDOFF.md (which tracks live state across conversations)
- Slicer profiles and gcode files (which are the actual print instructions)
- Physical fit verification (the guide tells you how to bolt; whether the seam is good
  is what you check after bolting)

## Provenance

Captured from the v021 sled 2×2 bolt-up guide (2026-11-26). The workflow rendered 6 views
from actual STL files via Blender EEVEE and composed a 4-page PDF with reportlab.
Generalized: tile coordinates, bolt positions, member layout, part naming, hardware counts.
Not verified: guide accuracy for assemblies other than half-lap tiled frames.
