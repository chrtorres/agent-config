# Material variants on shared geometry

Use this workflow when a model needs multiple finishes, colorways, or reference-driven surface patterns. The reviewer can switch between variants at the same camera angle, zoom, and pan.

## Build and review

1. Preserve the preceding revision. Within the new revision, give each variant a stable slug and a subdirectory. Agree on the inherited scale, orientation, silhouette, topology, UVs, and landmarks. If geometry differs intentionally, record which parts changed and whether the existing camera framing still fits.
2. Research distinguishing surface features before generating textures. Record what each source establishes and distinguish original patterns from a measured reconstruction. Model profile changes and major relief. Use a tangent normal map for small relief, a base-color map for pigment, and linear roughness/metallic channels for the surface response. Keep UV placement stable across variants. Check that geometry and normal-map detail combine at the intended strength.
3. Generate each editable Blender scene and separate asset-only GLB. Pack the maps and record units, axes, envelope, material inputs, and mesh counts. Render the same wide and detail views under the same studio lighting for every applicable variant. Inspect both the Blender previews and the browser, where lighting and support for Blender-specific shading can differ.
4. Use the collection viewer with same-origin HTTP. Keep the camera fixed when swapping equally framed assets. Commit metadata and downloads with the loaded GLB. Abort superseded fetches, discard stale decoder results, and preserve the last working model if an asset fails. Keep the previous revision available during review.
5. Reimport each delivered GLB. Check mesh names, units, bounds, topology, packed maps and material hookups against its source scene. Where the brief specifies shared geometry, compare decoded positions and indices across exports and verify distinct material data. Rebuild from an isolated source copy. Run the browser switch, same-camera, error-recovery, and rapid-selection checks, plus the general multi-shape [review smoke workflow](interactive-smoke-testing.md) when changing a viewer. Preserve the preview sheet, logs, and hashes with the version. Record the exact variant if the user approves it for a subsequent print workflow.

## Portable example

The bundled example is an original koi sculpture inspired by public variety standards. It generates the anatomy for five named palettes on the same pose. The starter builds two by default. Change the chosen variants, texture resolution, and render settings through the launcher options.

```sh
python3 <skill-directory>/scripts/create_material_variant_example.py \
  --output <new-version-directory> --version <revision>
python3 <skill-directory>/scripts/check_variant_collection.py <new-version-directory>
python3 <new-version-directory>/source/compare_renders.py <new-version-directory>
python3 <skill-directory>/scripts/launch_interactive_viewer.py \
  --directory <new-version-directory> --port <review-port>
```

Open the served `/review/` path. Use the same launcher with `--texture-width 1024 --preview-percent 30 --samples 6` for a quick verification run. The example needs Python 3, Blender 4.5 LTS with its bundled NumPy and glTF importer/exporter, and a Chromium-compatible WebGL browser. The contact sheet uses Pillow and discoverable DejaVu fonts. Override the font paths with `--serif-font` and `--sans-font` where needed. The viewer works offline with the included Three.js modules.

The example invokes the Blender verifier for each variant. The cross-variant checker expects the Blender export layout and hashes its tightly packed POSITION and index buffer views. If adapting it to assets with transforms, several accessors sharing a buffer view, or compressed attributes, check decoded coordinates, indices, and transforms. The generated example keeps transforms and export layout consistent.

Run the browser checks with Node.js, Playwright and its matching Chromium install in isolated storage. Install Playwright and Chromium there if they are missing. Test using the module resolved from the test script or pass an absolute path to the installed Playwright module as the final argument.

```sh
node <skill-directory>/tests/check_material_variants.mjs \
  <review-url> <evidence-directory> <playwright-module>
```

## Viewer data contract

Serve the version root. Keep `review/index.html`, `review/catalog.json` and the viewer dependencies together. The catalog chooses the files at `variants/<variant-slug>/review/model.glb` and `variants/<variant-slug>/review/metadata.json`. The matching scene and hero image live at `variants/<variant-slug>/<variant-slug>.blend` and `variants/<variant-slug>/preview/three-quarter.png`.

- `title` names the collection. `variants` is an ordered list of `{slug, label}` objects. Use distinct lowercase URL-safe slugs with optional internal hyphens. The first entry is the default.
- Each metadata file contains a `title` matching the corresponding label, a `status` with revision and review state, short `facts`, and a `note` explaining inspection highlights.
- Optional `detail` contains a button `label`, fractional `min` and `max` bounds in GLB-world XYZ, and a nonzero view `direction`. Use increasing fractional bounds between zero and one along each axis, measured from the full asset envelope. Omit the detail block when a preset is unnecessary.
- The bundled viewer assumes consistently oriented static assets with a shared envelope. Reframe on variant change when bounds or orientation are intentionally different. Use the multipart review workflow when the user needs part motion or isolation.

The collection ships asset URLs derived from the local catalog and keeps review state in the browser. It does not require an account or live data source. See [capture provenance and resource inventory](material-variants-provenance.md).
