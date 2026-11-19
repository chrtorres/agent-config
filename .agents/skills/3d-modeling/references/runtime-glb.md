# Versioned Blender assets for a runtime

Use a runtime GLB when a game or browser scene needs reproducible authored geometry. Agree on dimensions and units, forward and up axes, origin, node names and attachment points, animation type, materials, and a performance budget. Decide whether motion uses rigid pivots, a skeleton, or procedural transforms. This contract is distinct from collision and print tolerances.

1. Build geometry around a stable root. Parent limb geometry in pivot-local coordinates so rotating one joint does not move other branches. Apply scale and ground alignment to the hierarchy together. Preserve attachment names and declare any renames to application consumers.
2. Export only runtime geometry and pivots. Keep studio floor, lights and cameras in the authored `.blend` and inspection renders. Preserve the generator, front and rear renders, GLB and metadata under the model version.
3. Reimport the actual export. Check scale, ground offset, hierarchy, a real transform at each required pivot, included material/texture resources, and triangle and mesh counts. DCC bounds and export bounds can differ when curves or modifiers become meshes. Record the consumer format's axis conversion.
4. Copy the exact checked bytes into the version's interactive review and record their hash. Use the existing viewer for silhouette, zoom, orbit and material inspection. In an app, also verify the exact runtime asset through the application's load path, including any asynchronous replacement of fallback geometry. Verify that attachments remain parented to the loaded pivots. If the runtime must be offline, ship dependencies locally. The existing review viewer has a CDN dependency.
5. Record visual review and integration state for this version. Apply print-specific approval and slicing checks only when the user requests a physical deliverable.

## Reproduce the runtime character fixture

```sh
blender -b --factory-startup --python-exit-code 1 --python <skill-directory>/scripts/create_runtime_character.py -- --output <new-version-directory> --version <version> --height 1.8 --preview-percent 25
blender -b --factory-startup --python-exit-code 1 --python <skill-directory>/scripts/check_runtime_character.py -- --asset <new-version-directory>/model.glb --metadata <new-version-directory>/metadata.json
cp -R <skill-directory>/assets/interactive-review-viewer <new-version-directory>/review
cp <new-version-directory>/model.glb <new-version-directory>/metadata.json <new-version-directory>/review/
python3 <skill-directory>/scripts/launch_interactive_viewer.py --directory <new-version-directory>/review --port <available-port>
```

Run the viewer launcher with the selected review directory and an available port. Open its HTTP link and inspect orbit, reset and wireframe. The generator requires Blender with glTF import and export, and uses a small CPU render preview when invoked as shown. The output directory must be new. The validator checks the GLB container, resources, actual imported bounds and pivot motion. It prints the exact GLB SHA-256 and actual mesh and triangle counts. The example uses rigid nodes and carries no skin, collision hull, LODs or animation clips. Test the engine's actual importer and budgets separately.

## Capture decision and provenance

The incoming method is authoring a parametric game asset with a measured runtime contract and versioned browser review. Factors follow the skill capture rubric in order: outcome, inputs, procedure, resources, validation.

| Candidate | Factors | Score | Evidence and routing |
| --- | --- | ---: | --- |
| 3D modeling | .75, .75, .75, .75, .75 | 75% | Already covers parametric Blender, version folders, studio renders, exact GLB review, and measured bounds. Runtime axes, pivot motion and export subset warrant a targeted extension. |
| Smoke test | .5, .5, .5, .75, .75 | 56.25% | Can test delivery and controls using synthetic GLBs. It does not define an authored runtime hierarchy or export constraints. Reuse viewer QA as appropriate. |
| Full-stack app creation | .5, .5, .5, .5, .5 | 50% | Covers runtime loader verification on an application journey. It does not own Blender geometry or GLB export. Keep that role in modeling. |

| Resource | Disposition |
| --- | --- |
| Authored parametric character generator | Adapted into [create_runtime_character.py](../scripts/create_runtime_character.py). Source defines the original asset's proportions and transformation method. Example names, output layout and metadata are portable. |
| Structural and behavioral checks | [check_runtime_character.py](../scripts/check_runtime_character.py) verifies the generated binary with Blender and the Python standard library. The existing viewer and its tests remain in use. |
| GLB, Blender scene, images and metadata | Regenerate from source. The original exports, screenshots and manifests remain in task evidence. The regenerated fixture is a separately versioned verification asset. |
| Supplied visual inspiration, game shader and cloth animation, physical hardware, dependencies | Original imagery and game-specific effects remain task-local. App validation routes to [playable 3D regression](../../full-stack-app-creation/references/playable-3d.md). Blender and a WebGL browser are external. |

Historical feedback, paraphrased. The user wanted an inspectable playable character and a specific visual direction. The asset used named pivots for game motion and kept studio objects outside the GLB. Integration later needed to restore runtime attachments after asynchronous model replacement. Historical structural, browser and asset checks passed for the original character and viewer. This evidence covers visual and runtime behavior, with no physical print checks.

Generalized values include task and version identifiers, project paths, local ports, camera review locations and output filenames. The example's height and proportions describe synthetic fixture geometry.
