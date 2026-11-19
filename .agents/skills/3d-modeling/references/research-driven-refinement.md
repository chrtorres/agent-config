# Research-driven realism and reference review

Use this workflow when the model is intended as a visual reference, when the internal structure matters, or when feedback calls for greater realism. Keep the initial model and each accepted set of reference renders independently reproducible.

1. Define the object, reference class, units, axes, handedness, orientation, and allowed inferences before editing. Derive left and right from the object's frame. Keep general background references separate from evidence about the exact variety, specimen, or product revision. Prefer original studies, official drawings, scans, and dissection or teardown reports. Record figure or table identifiers where available.
2. Maintain a source-to-feature ledger. For each feature, record the claim, observation, source, applicable population or version, modeled decision, uncertainty, and a check the result can fail. If multiple sources disagree, specify what differences in scale, specimen condition, or measurement could explain it. Keep model-derived dimensions separate from observed ones.
3. Script the revision from a known base. Establish scale and reference landmarks first. Correct topology, side, connectivity, and relative positions before adding fine relief or material detail. Choose parametric shapes, lofts, paths or measured meshes as suited to the evidence. Define representative details as such, especially invented small branches and inferred surfaces.
4. Render comparable poses plus useful viewing angles. Include an isolated close-up when a major feature is hidden. Review images and objective checks together. An early silhouette match can coexist with a fit or connectivity error. Correct the source, regenerate, and rerun the affected checks. Retain the receipt for failed drafts alongside the passing evidence.
5. Check selected dimensions, relationships, component counts, and explicit tolerances. Use independent, matched geometry or calibrated measurements to make specimen-level claims. Use sampled envelope checks only to flag projected fit relative to the authored model. A sample pass does not establish true anatomical dimensions, exact edge clearance, or fit over every triangle.
6. Export the exact reviewed GLB, keep a stable hierarchy, and verify the export in a separate load. Supply optional assembled presets, part offsets, nested structures and evidence links in the [viewer metadata](../assets/interactive-review-viewer/README.md). Attach the reliability and limitations to the structure group in the review. Keep visual review and any applicable print approval separate.

## Runnable example

The bundled synthetic assembly exercises two shaped components, a contextual cover, hidden geometry, child-level inspection, and a closed envelope gauge. It has no measured real-world counterpart. Use Blender with glTF support, Python, Node.js, Playwright Chromium and its software or hardware WebGL runtime. Offline browser checks use the pinned Three.js 0.180.0 package with its license. Obtain it with `npm pack three@0.180.0` and extract it to an isolated dependency directory.

```sh
blender -b --factory-startup --python-exit-code 1 \
  --python <skill-dir>/scripts/create_reference_fixture.py -- <fixture-dir>
blender -b <fixture-dir>/fixture.blend --python-exit-code 1 \
  --python <skill-dir>/scripts/check_reference_envelope.py -- \
  --envelope "Reference envelope" --feature Hub --feature Ring --tolerance-mm 1
python3 <skill-dir>/scripts/prepare_reference_review.py <fixture-dir>/fixture.glb \
  --metadata <fixture-dir>/metadata.json --three-dir <three-package-dir> \
  --output <review-dir> --no-screenshot
python3 <skill-dir>/scripts/launch_interactive_viewer.py --directory <review-dir> --port <port>
node <skill-dir>/tests/check_reference_review.mjs <review-url> <evidence-dir> <playwright-module>
```

Run the fit check again with the same hub and the lid as the envelope. The mismatch must fail. For real geometry, provide closed outward-oriented evaluated geometry as the reference mesh and use the appropriate scene units. The nearest-oriented-surface test samples authored vertex positions with object transforms. Bake required modifiers before using it. Inspect flagged positions near concave boundaries, oral openings, or sharp edges. Use [calibrated landmark checks](photo-based-refinement.md) for measured correspondence.

[Capture comparison, feedback and resource inventory](research-driven-refinement-provenance.md)
