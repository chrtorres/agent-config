# Combined review workspaces

1. Inventory each authored runtime asset, driving metadata and relative dependencies. Preserve the exact GLBs and check whether the views share a rig or reconstruct different states. Record the basis of each view and what the browser can validate.
2. Preserve the existing scene controls, sources and downloadable files. An exploded view needs named parts, offsets, callouts, isolation and reassembly. For movement, distinguish a live history trace from a planned or baked course. Record which clock drives each scene.
3. Package the prepared review folders with the [workspace builder](../scripts/combine_reviews.py). The browser shell lazy-loads views, keeps instantiated canvases sized and suspends inactive rendering and simulation. See the [adapter and trace contract](../assets/interactive-review-viewer/README.md#workspace-lifecycle-and-path-sampling).
4. Rebuild in isolated storage and verify switching while playback is active. Confirm that the paused state, camera and mesh selection survive switching and that repeat reassembly restores geometry. Test a broken child asset and verify that another view remains usable. Record hashes of the exact reviewed artifacts.

## Synthetic reproduction

Use Blender 4.5 LTS, Python 3.10+, Node.js and Playwright Chromium with WebGL. Obtain Three.js 0.180.0 with npm and extract the package as the offline dependency. Generate a moving asset and a multipart fixture.

```sh
blender -b --python-exit-code 1 --python <skill>/scripts/create_motion_fixture.py -- \
  --kind flexible --output <scratch>/moving
blender -b --python-exit-code 1 --python <skill>/scripts/create_reference_fixture.py -- <scratch>/static
```

Prepare reviews using the following command pattern. Use the moving fixture for context and motion and the static fixture for parts.

```sh
python3 <skill>/scripts/prepare_reference_review.py <fixture>/fixture.glb \
  --metadata <fixture>/metadata.json --three-dir <three-package-directory> \
  --no-screenshot --output <scratch>/<view-id>
```

Save this manifest beside the three prepared directories.

```json
{"title":"Assembly study","views":[
  {"id":"context","label":"Context","directory":"context"},
  {"id":"motion","label":"Motion","directory":"motion"},
  {"id":"parts","label":"Parts","directory":"parts","exploded":true}
]}
```

```sh
python3 <skill>/scripts/combine_reviews.py <scratch>/workspace.json --output <scratch>/combined
python3 <skill>/scripts/launch_interactive_viewer.py --directory <scratch>/combined --port <port>
node <skill>/tests/check_combined_review.mjs <review-url> <evidence-directory> <playwright-module>
```

[Capture decision and resource inventory](combined-review-provenance.md)
