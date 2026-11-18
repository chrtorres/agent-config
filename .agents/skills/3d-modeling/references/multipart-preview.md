# Multipart previews and print-part inspection

Use the interactive assembly preview before design approval. During print preparation, link a separate view of the meshes actually being handed off. Keep both under the same model version. A display-only layout change can retain the existing approval if the geometry and export identities still match.

## Interactive assembly

1. Export the assembly GLB with a unique, stable name for each top-level part node. A node may contain multiple meshes. Keep guides at their own top-level nodes and keep the GLB in its assembled pose.
2. In the [viewer template](../assets/interactive-review-viewer/), add a `parts` array to `metadata.json`. Each entry has a `node` string matching the exported GLB name, a readable `label`, and an `offset` array with three finite translation values in the GLB node's parent axes and units. For example, a synthetic `Fixture plate` can have `"offset": [-24, 0, 0]`. Blender's default glTF export uses Y-up, so verify axes and scale from the actual GLB. List every inspectable physical part. Unlisted root children will be hidden as guides when exploded. Leave `parts` empty for a single-part model.
3. Show the assembled state on load. **Explode** moves parts from their saved assembled positions and reveals **Inspect part**. Selecting a part hides the others and fits the camera to it. **All parts** returns to the exploded layout. **Reassemble** restores all original positions and the assembly guides. Keep Reset, orbit, pan, zoom, and wireframe usable while inspecting parts. The template honors reduced motion.
4. Check orientation, visible gaps, clipping, and reachability of controls at desktop and narrow widths. Explosion offsets are a presentation device. Use [assembly refinement](assembly-refinement.md) when verifying actual insertion paths, interference, or retention.

## Standalone print-mesh sheets

Export and validate the approved parts at their intended scale. Keep one mesh file per part. Record hashes, dimensions, and the files selected for handoff. If a combined package is requested, re-import it and verify its part count and scale. Some slicer CLIs process multiple named inputs as separate exports to the same destination, which can leave only the last input. An assembled package may require rearrangement for the printer bed.

Create a print-preview manifest beside the approved exports. The bundled [builder](../scripts/build_print_previews.py) reads the manifest and hands the geometry to the [Blender renderer](../scripts/render_print_meshes.py). The manifest has:

- A `title` and `version` for the sheets, plus `units` set to `"millimeters"`.
- `parts` containing one entry per individual STL selected for handoff. Each entry has a path `file` relative to the manifest, a user-facing `label`, its full SHA-256 hex digest in `sha256`, and a three-number `offset` in the STL's XYZ coordinate system and millimeters.
- Optional `assembly_translation` in the same axes and units when an STL has been translated for print placement. STL meshes should already use consistent assembly axes. If orientation differs, reconcile it explicitly before rendering the assembly.

Render the two sheets:

```sh
python3 "<skill-dir>/scripts/build_print_previews.py" \
  --manifest "<print-prep-dir>/print-preview.json" \
  --output "<print-prep-dir>/preview"
```

The renderer checks each individual STL against its hash, measures its original extents, and applies translations only to the render scene. The builder writes `exploded-print-parts.png` with a part key and `individual-print-parts.png` with individually framed pieces, filenames, and dimensions. Inspect both sheets and tune offsets if parts or annotations overlap. The browser GLB may include assembly guides. The print sheets read only the explicitly listed print meshes. The renderer's check does not replace mesh validation, slicing, or fit testing.

## Isolated reproduction

Run the synthetic fixture to exercise both paths without project inputs. Set `skill_dir` to an isolated copy of this skill and `run_dir` to a new retained sandbox.

```sh
blender -b --factory-startup --python-exit-code 1 \
  --python "$skill_dir/tests/fixtures/create_multipart_review.py" \
  -- --output "$run_dir/fixture"
python3 "$skill_dir/scripts/build_print_previews.py" \
  --manifest "$run_dir/fixture/print-preview.json" \
  --output "$run_dir/fixture/print-preview"
python3 "$skill_dir/tests/check_multipart_viewer.py" \
  --review "$run_dir/fixture/review" --sandbox "$run_dir/browser"
python3 "$skill_dir/scripts/run_interactive_review_smoke.py" \
  --sandbox "$run_dir/single-part"
```

The multipart smoke test also accepts a caller's review directory. It copies the viewer into the sandbox, serves it over HTTP, drives real browser events, and records render visibility, configured offsets, guide visibility, each part's isolation, camera controls, reduced motion, and exact positions after repeated reassembly. Keep the result log and screenshots with the sandbox. The single-part suite complements it with more shapes and lighting configurations.

Prerequisites: Blender 4.5 LTS or a compatible version, Python 3.10+ with Pillow and the DejaVu Sans font for the sheets, and Python `websocket-client` plus a Chromium-compatible browser with WebGL for the multipart test. The viewer loads pinned Three.js modules from jsDelivr. Discover Blender and Chromium on PATH or pass `--blender` or `--chrome` to the corresponding tool. Use `node --input-type=module --check < viewer.js` for an optional standalone JavaScript syntax check.
