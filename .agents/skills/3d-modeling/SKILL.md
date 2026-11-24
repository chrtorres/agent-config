---
name: 3d-modeling
description: Create and revise parametric Blender models with versioned browser review. Use for photo-based reconstruction, breed- or standard-correct anatomy with an individual's coat markings, multipart inspection, material variants, runtime GLB assets with named pivots, code-generated video, and approved print exports.
---

# Iterative 3D modeling and print preparation

Use this skill when the user asks for a new 3D model, a revision to an existing model, or preparation for 3D printing. Keep authored source, previews, and exports in a titled run directory. A model is not approved merely because Blender generated it: the user must review a rendered preview before STL/Blend delivery is treated as approved for printing.

## Procedure

1. Read workspace instructions and inspect the available modeling, mesh-repair, and slicing tools. Discover executable paths and versions at runtime.
2. Title the run and create its project parent under the workspace-root `creations/` directory. Use the layout `<workspace-root>/creations/<project-name>/version-001/`, with later revisions in sibling directories such as `version-002/`. Keep each version's source, previews, and exports together inside its version directory; do not place creation artifacts in the workspace root or in an unrelated directory.
3. Translate the request into observable geometry requirements: units, overall dimensions, thicknesses, clearances, tolerances, intended use, and any print-orientation constraints. Resolve routine assumptions explicitly in the run notes.
4. Create a parameterized Blender source script. Prefer reproducible construction from primitives or other inspectable operations over an unrecorded interactive edit. Save the `.blend` and source only in the current version directory.
5. Render a review preview from the generated Blender model. Show enough angles or detail to inspect silhouette, openings, interfaces, thickness, and likely print issues. Build the interactive review from the same version before requesting approval. For multipart models, use [multipart-preview.md](references/multipart-preview.md) and [exploded-part-labels.md](references/exploded-part-labels.md) to provide Explode, labeled callouts, individual inspection, and Reassemble.
6. Stop for user review. Ask for approval or concrete feedback; do not call the STL/Blend final or continue to slicing/printing on the basis of a generated file alone.
7. If rejected or revised, record the feedback as observable changes and identify which requirements carry forward. Create the next sibling version, preserve the prior evidence, and rerun the checks affected by the revision. For interlocking or multipart revisions, use [assembly-refinement.md](references/assembly-refinement.md) to choose a joint, check assembly motion and retention, and present an exploded or detail view alongside the assembled view. Repeat the review gate.
8. Record explicit approval against the exact version and previews reviewed. Material changes to the design restart review. Prepare the requested print exports from the approved geometry at the intended physical scale. Run the relevant mesh and slicer checks, record settings, and distinguish CAD verification from printed fit and strength. Physical printing requires separate authorization.
9. For multipart print prep, provide separate exploded and individual print-part sheets under `print-prep/preview/`, rendered from the individual meshes being handed off. Label pieces with STL filenames and measured dimensions. Use the [multipart preview builder](references/multipart-preview.md). Viewer-only changes can stay with the approved version when the geometry and print-file identities are verified.

## Refining an existing artifact

Use [product-refinement](../product-refinement/SKILL.md) for a revision that needs a measured baseline and coordinated visual, modeling and browser checks. Keep the modeling version and review gates in this skill.

For a reference-led concept that preserves an approved subassembly while several revisions are exposed through one review app, use [versioned concept refinement and handoff](references/versioned-concept-handoff.md). It covers exact mesh and local-transform comparison, runtime-safe procedural appearance, concept-versus-fabrication labels, compact evidence and cleanup-aware handoff.

## Runtime assets

For a Blender asset intended for a game or browser scene, use the [runtime GLB workflow](references/runtime-glb.md). It defines an engine-facing asset contract, separate studio and runtime exports, and validation of the exact GLB used in the browser. Print approval applies only to physical outputs. For authored foliage used in a playable world, see [runtime vegetation](references/runtime-vegetation.md). For fitted gear and expressive faces, use [runtime character fit](references/runtime-character-fit.md) to check rear clearance, facial poses, and moving attachment anchors. For cloth tails, sashes or ribbons that move with the character, use its [soft attachments in motion](references/runtime-character-fit.md#soft-attachments-in-motion) section and the [cloth collider example](assets/cloth-collider-example/README.md): collide against a measured, bone-attached silhouette, not a fixed capsule. To extend that motion across a whole outfit (skirt panels, wide sleeves, tied hair under a hat) or after a fit change, use [one cloth style across a whole outfit](references/runtime-outfit-cloth.md) and re-measure the collider with [measure_body_profile.py](scripts/measure_body_profile.py).

## Research-driven animation

Use [animated figure review](references/animated-figure-review.md) for a figure that deforms, articulates, or travels through a scene. For baked motion, author poses and root motion in Blender, bake named clips, and inspect the exported GLB in the browser. For procedural motion, publish the consumer pose code with the exact GLB and verify motion through rendered observations. The bundled generator covers both rigid pivots and a weighted skeleton. Connect observed motion to measurable checks and state which parameters were inferred.

## Code-generated video

Use [code-generated video](references/code-video.md) for Python or Blender animation delivered as MP4. Generate frames and audio on a declared timeline, encode and verify the actual artifact, and use the included synthetic smoke runner. For authorized recorded-media preservation, verify encoded samples, decoded content and timing, then compare container bytes when required. See the [capture decision](references/code-video-provenance.md). For video from the actual playable renderer, use [deterministic browser gameplay reels](references/browser-gameplay-reel.md).

## Interactive footage motion

Use [reference-driven motion and localized footage edits](references/footage-motion.md) for stable bind landmarks, occlusion-aware retargeting, source-preserving edits, or photo-textured movement over recorded footage. For private source comparisons, use temporary processing and retain only synthetic fixtures and de-identified results.

For a local editor that regenerates its pose, masks, and editable surface from the caller's video alone, use the source-only preparation and validation procedure in that reference. The [standalone editor](../full-stack-app-creation/assets/footage-editor/) provides the runnable engine and tests.

For localized facial edits in video, use [motion-aware face compositing](references/face-motion-compositing.md) to protect current-frame eyes, preserve the performer's mouth interior (teeth, tongue, cavity), handle occlusion by hands or objects with the XSeg model, inspect relative-depth bands, and control seam lag during quick movements. When a face swap blurs, wobbles or lands on the wrong face during fast action, use its [two-pass action tracking](references/face-motion-compositing.md#tracking-faces-through-action) and score it on a synthetic clip with known motion. Score expression preservation and occlusion handling with the [expression and feeding benchmarks](../full-stack-app-creation/references/inline-video-face-swap.md#benchmark-expression-preservation-and-occlusion).

For reviewer feedback on a completed swap, compare the original and composite in the main viewer at the same playhead. Keep a sidebar inspection view synchronized to the displayed frame. Verify a switch back after playback or seeking, then check protected pixels in the lossless export. See [the comparison and recovery workflow](../full-stack-app-creation/references/footage-comparison-and-export.md).

When a resized body part looks like a magnifying glass, follow [reshaping without a lens effect](references/footage-motion.md#reshaping-without-a-lens-effect). Add [soft-tissue follow-through](references/footage-motion.md#soft-tissue-follow-through) for enlarged regions that should move with the body, and use [hair and feature colour](references/footage-motion.md#hair-and-feature-colour) for luminance-preserving dyes with temporal hair stabilization and edge-aware joint bilateral upsampling.

When a tracked edit must survive format conversion, variable frame timing, or a 4K retry, use the [footage clock and rendition checks](references/footage-motion.md#footage-clock-and-rendition-checks).

## Context and inspection for the same asset

For a model shown in a composed environment and at close range, use [context and inspection renders](references/context-and-inspection.md) to stage the surroundings, compare isolated silhouettes and details, and verify the exact runtime exports.

## Combined review workspaces

Use [combined review workspaces](references/combined-review-workspaces.md) when a contextual scene, animated study and a multipart inspection need a shared entry point. Package the tested review assets together and verify each view's visible state, lifecycle, download and source metadata.

## Registered layers and secondary motion

Use [registered assembly study](references/registered-assembly-study.md) to fit layered reference meshes, preserve attachment pivots and verify an exported physics review. See the [capture decision](references/registered-assembly-provenance.md) for provenance and resources.

## Material variants

When several colorways or finishes share a model, use the [material-variant workflow](references/material-variants.md). Keep shared geometry and UVs consistent, generate editable scenes and textured GLBs for each variant, and use identical studio views and a browser selector that preserves the inspection camera. Run the bundled [worked example](assets/material-variant-example/README.md) to reproduce the texture, export, and review pipeline.

## Photo-based reconstruction and refinement

Use [photo-based refinement](references/photo-based-refinement.md) when matching a physical object from photos, dimensions, manufacturer diagrams, or teardown exhibits. Fit the visible landmarks, document uncertainty and hidden geometry, and verify any requested fidelity threshold against independent evidence. Retain the source, matched views, measurements, and browser smoke results with the version.

For a multipart photo reconstruction, research the exact manufacturer/model first, prioritizing manufacturer pages and manuals, regulatory external/internal photos, and orthogonal teardown or underside views. Record source URLs and what each source establishes. Calibrate visible landmarks before adding detail, then represent every inspection-worthy physical piece as a stable top-level node. Populate the review metadata `parts` contract and require numbered callouts, leader lines, a part key, click-to-isolate behavior, and exact reassembly restoration. A 3D review demonstrates correspondence and inspectability; it cannot prove a 99% visual match without a documented comparison protocol and independent views.

## Robot description from a reconstruction

Use [robot description](references/robot-description.md) when a multipart model must become a URDF for robotics or simulation. That covers a REP-103 frame, parts that pivot on their joint axes, inertials and centre of mass, collision primitives, sensor frames, and a spec that tags each value as sourced or estimated. Verify the result with:
- [check_interference.py](scripts/check_interference.py), a Blender BVH audit with an allowlist and a joint-pose sweep
- [check_urdf.py](scripts/check_urdf.py)
- [merge_glb_animations.py](scripts/merge_glb_animations.py), which builds a single joint-exercise clip
- [compare_glb_exports.py](scripts/compare_glb_exports.py), for regeneration

Inject faults to confirm the checks catch them. Tests are in [test_robot_description_tools.py](tests/test_robot_description_tools.py). Provenance is in [robot-description-provenance.md](references/robot-description-provenance.md).

## Localized still-photo edits

For an authorized still-image edit, use the [localized photo face-swap workflow](../full-stack-app-creation/references/photo-face-swap.md) to fit facial landmarks to a target portrait. Keep the fit, face mask, full-resolution result, and comparison together in the version directory. Open the comparison in a visible browser when handing it to a desktop reviewer.

## Research-driven realism

Use [research-driven refinement](references/research-driven-refinement.md) when a model will be referenced for accurate form, internal structure, or material appearance. Tie each correction to a source and an observable check. Use the bundled Blender and browser fixture to reproduce scripted fit checks, layered presets, nested isolation and evidence-linked review.

## Breed-standard anatomy with an individual's coat

Use [standard anatomy and coat](references/standard-anatomy-and-coat.md) when a specific animal or unit should take its form from the governing public standard while only named features (coat colour and markings) stay individual. Turn clauses into checks measured on the mesh, register side renders on the standard's exemplar figures, carry markings through the same warp that reshapes the form, research anatomy before fixing reported faults, identify photo sides before reading markings, and build printable fleck colours with a grid-boundary guard. Synthetic helpers: [sdf_coat_demo.py](scripts/sdf_coat_demo.py), [register_exemplar_overlay.py](scripts/register_exemplar_overlay.py), [sweep_params.py](scripts/sweep_params.py) and [photo_measure_grid.py](scripts/photo_measure_grid.py), tested by [test_standard_and_coat_tools.py](tests/test_standard_and_coat_tools.py).

## Patterned spherical frame workflow

For a request to turn a sphere into a patterned frame, use the sphere as the preserved design intent and create the frame as a new sibling version. Keep the solid sphere version intact for comparison.

1. Define the frame parameters before modeling: target outer diameter, nominal strut or rod diameter, number of pattern families, number of bands per family, wave amplitude/frequency, and intended print process. If the user names a pattern such as gyroid, distinguish a true implicit-surface gyroid from a gyroid-inspired visual approximation in the run notes and handoff.
2. Prefer a parameterized construction. A portable baseline is three families of closed, sinusoidally wavy spherical bands, rotated about orthogonal axes and phase-shifted so the bands interweave into an open repeating pattern. Generate the bands as beveled 3D curves, convert them to mesh, join them into one named frame object, and smooth the resulting faces.
3. Preserve the target envelope by generating band centerlines inside the requested radius and accounting for bevel/strut radius when selecting the path radius. Validate the resulting bounding-box dimensions rather than assuming the mathematical path radius equals the finished outer diameter.
4. Render the frame from a three-quarter angle with lighting that reveals both struts and openings. Inspect for a readable silhouette, adequate openings, unintended tangencies or self-intersections, uniform-looking strut thickness, and regions that may be difficult to print or clean.
5. On feedback, create the next sibling version and change only the affected parameters where possible. Typical refinements include reducing band density, increasing openings, changing wave amplitude or phase, thickening struts, or adjusting the camera and lighting for review. Do not overwrite the prior preview or source.
6. Before approval, verify that the source regenerates the frame, the result is the expected single mesh component (unless the user requests multipart geometry), and the dimensions remain within the stated tolerance. Do not export STL/3MF until the user approves the exact patterned-frame version and preview.

## Reproduction resources

- [scripts/create_box_frame.py](scripts/create_box_frame.py) is a portable parameterized Blender example for an open cubic frame.
- [scripts/render_preview.py](scripts/render_preview.py) renders a three-quarter inspection image from a generated `.blend`.
- [scripts/launch_interactive_viewer.py](scripts/launch_interactive_viewer.py) serves a required versioned GLB review directory over HTTP.
- [scripts/smoke_model_generator.py](scripts/smoke_model_generator.py) generates synthetic geometry and shadow variants for viewer smoke testing.
- [scripts/run_interactive_review_smoke.py](scripts/run_interactive_review_smoke.py) runs the retained multi-shape browser smoke workflow and enforces the minimum check count.
- [assets/interactive-review-viewer](assets/interactive-review-viewer) is the portable interactive browser viewer template.
- [tests/test_interactive_viewer_template.py](tests/test_interactive_viewer_template.py) checks the viewer template contract and portable paths.
- [tests/test_interactive_smoke_runner.py](tests/test_interactive_smoke_runner.py) checks smoke-runner entrypoint and portability.
- [references/interactive-smoke-testing.md](references/interactive-smoke-testing.md) explains the generalized smoke-test workflow, learning goals, and cleanup boundary.
- [references/resource-disposition.md](references/resource-disposition.md) records what was captured from the originating run, what was generalized, and what remains an external prerequisite.
- [references/comparison-and-feedback.md](references/comparison-and-feedback.md) records the existing-skill comparison and the user feedback that established the preview/approval gate.
- [tests/test_box_frame_workflow.py](tests/test_box_frame_workflow.py) runs a small end-to-end geometry check when Blender is available.
- [references/assembly-refinement.md](references/assembly-refinement.md) includes an isolated Blender reproduction of a flush rail-to-rail dovetail revision, with model generation, collision and retention checks, and two preview renders.
- [references/multipart-preview.md](references/multipart-preview.md) documents the reusable explode/inspect controls, print-mesh sheets, and multipart smoke test.
- [references/exploded-part-labels.md](references/exploded-part-labels.md) documents the generalized labeled-callout contract for multipart exploded review.
- [scripts/check_preserved_subassembly.py](scripts/check_preserved_subassembly.py) verifies that selected mesh topology, vertex coordinates and local transforms remain exact across Blend files while allowing presentation materials to change.
- [references/versioned-concept-handoff.md](references/versioned-concept-handoff.md) coordinates multi-revision reference matching, approved-subassembly identity, review-app integration and transfer cleanup.

The examples were tested with Blender 4.5 LTS on PATH. Choose mesh repair or slicing tools to suit the requested print workflow and report the checks that actually ran. The example generators and renderers accept caller-supplied output locations.

## Validation and delivery

For a new model, validate at minimum:

- the source script runs from an isolated copy;
- the generated object has the requested dimensions and expected component count;
- the preview exists and is visually inspectable;
- any STL/3MF is generated only after approval and is checked with the selected mesh/slicer tool.

Keep fresh run evidence under `<workspace-root>/creations/<project-name>/version-###/`, outside this shared skill. In the handoff, link the run README, preview, source, and any approved exports separately, identify the exact approval state, and state whether slicing or physical printing occurred. If the user rejects the preview, treat the current version as unapproved and continue the loop with their feedback.

## Required interactive 3D review

Every new or revised modeling workflow must include an interactive browser review before the user approval gate. Add it under the current version directory, for example `<workspace-root>/creations/<project-name>/version-###/review/`. Use the reusable template in [assets/interactive-review-viewer](assets/interactive-review-viewer), copy in a caller-supplied binary glTF/GLB named `model.glb`, and provide a `metadata.json` file describing the review version, envelope, units, pattern, and approval state. A static render alone is insufficient for review completion.

1. Export the exact reviewed geometry to GLB without replacing the authored `.blend`, source script, or rendered preview. Keep the export tied to the same version directory.
2. Serve the review directory over HTTP with [scripts/launch_interactive_viewer.py](scripts/launch_interactive_viewer.py). Do not rely on `file://` loading; browser module and GLB requests can be blocked by local-file security rules.
3. Provide orbit, zoom, pan, reset/fit view, optional auto-rotate, and a wireframe or inspection mode. Use readable lighting and show the model's review metadata and approval state beside the viewport.
4. Validate the viewer asset with an HTTP `200` check, JavaScript syntax check, and a browser smoke test that confirms the GLB renders. Inspect at least one screenshot and exercise the relevant controls when browser automation is available.
5. Before handing off a changed viewer workflow, run at least 20 smoke checks in an isolated sandbox. Cover the source/build path, GLB and metadata delivery, loading, rendering, and controls across multiple shapes and lighting setups. For multipart changes, also exercise real part movement, per-part visibility and framing, and exact restoration through repeated reassembly. Record check counts, artifacts, failures, and runtime versions in sandbox evidence.
6. Keep the smoke-test sandbox and its evidence outside the shared skill. Do not delete it automatically: leave it available for user inspection and ask for approval before cleanup. Cleanup approval applies only to the named smoke-test sandbox, not to authored creation runs.
7. Treat the interactive viewer as review evidence, not a substitute for Blender geometry checks, mesh repair, slicing, physical fit, or load testing. Stop at the same user approval gate; do not label the model printable or load-certified because the viewer loads successfully.

The template is intentionally portable: it uses Three.js from a documented external CDN at runtime, accepts any caller-supplied `model.glb`, and reads caller-supplied `metadata.json`. See [references/interactive-viewer.md](references/interactive-viewer.md) for the dependency, provenance, and compatibility limits.

For reusable smoke testing and learning, use [references/interactive-smoke-testing.md](references/interactive-smoke-testing.md) and [scripts/run_interactive_review_smoke.py](scripts/run_interactive_review_smoke.py). The generalized runner is separate from any task-specific smoke evidence and keeps its sandbox until explicit cleanup approval.
