# Photo-based reconstruction and refinement

1. Confirm identity and revision using labels, markings, and manufacturer references. Seek orthogonal and angled views, published envelope dimensions, service diagrams, and applicable regulatory teardown photos. Record which source supports each change. Preserve contradictory evidence and use the closest matching revision.
2. Define observable acceptance criteria before fitting. Record units, coordinate axes, datum, known dimensions, intended surface coverage, and measurement tolerances. For image measurements, use a known dimension in the same plane and axis, or rectify an oblique view with a calibrated camera. Record pixel picks, uncertainty, and effects such as perspective, editing, and unknown depth.
3. Build or revise a versioned parametric model. Keep stable part names, meaningful subassemblies, and geometry in the assembled pose. Trace silhouette, openings, and part interfaces from the best views. Label hidden mechanisms and inferred dimensions as estimates. Produce matched exterior views, service details and an exploded overview. In the viewer, use neutral lighting when finish and color are reference features.
4. Retain a geometry report with world-space part bounds. Use [compare_landmarks.py](../scripts/compare_landmarks.py) for planar axis-aligned spans or offsets. Supply millimeters and `part_bounds_xyz_mm` as named pairs of XYZ min/max vectors. The [sample landmark file](../tests/fixtures/photo-landmarks.json) shows signed pixel readings relative to the chosen datum, a positive calibration span, and reading allowance. Use `kind` of `span`, `center`, `min`, or `max` in the aligned mesh frame. Label each landmark as a fitting input or independent holdout. Report per-feature residuals and uncertainty. Check features beyond box extrema with matched overlays or measured surface comparisons.
5. Repeat the build in isolated storage. Compare geometry, node transforms, units, materials, and observable renders. If GLB bytes differ, report that separately and compare decoded mesh geometry at an explicit precision. Verify browser delivery, part isolation, and exact reassembly with the [multipart smoke test](multipart-preview.md).
6. Report calibration residuals, independently tested features, and unknown regions. A whole-model percentage requires a defined metric, adequate surface coverage, and independent dimensioned CAD or calibrated scans for the requested scope. Smoke checks validate review behavior. Retain the normal visual approval gate.

## Synthetic reproduction

From an isolated skill copy, use Blender 4.5 LTS and Python 3.10 or compatible versions:

```sh
blender -b --factory-startup --python-exit-code 1 \
  --python "<skill-dir>/tests/fixtures/create_multipart_review.py" -- --output "<run-dir>/fixture"
python3 "<skill-dir>/scripts/compare_landmarks.py" "<run-dir>/fixture/geometry.json" \
  "<skill-dir>/tests/fixtures/photo-landmarks.json"
python3 "<skill-dir>/tests/check_multipart_viewer.py" \
  --review "<run-dir>/fixture/review" --sandbox "<run-dir>/browser"
```

The synthetic fixture should yield a 0 mm plate residual and a 1 mm pad residual against synthetic image readings. Its overall fidelity field remains unverified.

## Capture record

The user supplied additional reference photos and requested a high-fidelity revision with smoke testing. The revision used model-specific manufacturer anatomy and teardown exhibits, calibrated visible landmarks, and checked regenerated geometry and interactive part behavior. Photo uncertainty and hidden geometry prevented acceptance of the whole-model percentage.

Using the skill-add rubric in outcome, scope, procedure, resources, and validation order, existing 3d-modeling scored **78.75%** (1, .75, .75, .75, .5). Versioning, parametric builds, multipart delivery, and review were already covered. Photo calibration and independent fidelity checks were missing. Smoke-test scored **33.75%** (.25, .25, .25, .5, .75). It covers browser delivery and behavior with synthetic inputs, while reconstruction and metrology are outside its scope. The user explicitly chose to extend 3d-modeling.

The generic comparison helper and synthetic inputs are bundled. Use the existing Blender fixture, GLB viewer, and smoke harness to regenerate artifacts. Obtain object-specific photos, scans, published dimensions, and documents separately. Product identifiers, local paths, source imagery, production meshes, and runtime logs stay in the original task evidence. Blender, Python, Chromium with WebGL, websocket-client, Pillow, and access to the viewer's pinned CDN are external prerequisites for the full reproduction.
