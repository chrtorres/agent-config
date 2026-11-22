# Context and inspection renders

Use this workflow for reference-led models delivered both in a composed scene and for close inspection.

1. Treat surroundings as part of the visual brief. Review the whole frame for contact shadows, surface transitions, scale cues and background silhouettes. Check a close view and at least one wide view. Include a separate silhouette with distracting context hidden and a detail view framed around the feature.
2. Keep lighting and staging editability in Blender. Export the subject and shared setting separately when consumers need to place or inspect the subject independently. Record meters or other declared units, axis conversion, origin and measured extents. Check that subject and setting align when loaded together. Use instancing for repeated detail when it fits the target renderer and measure the resulting draw and triangle costs.
3. Use camera depth ranges appropriate to each viewing scale. When layered ground flickers, inspect overlapping surfaces and tighten the near/far range as the view allows. Test close framing for clipping and wide framing for stable ground and distant objects. Refit against the separated bounds when an exploded view no longer fits the assembled camera.
4. Compare credited reference photos with the generated views at meaningful scales. Sample photo color to guide appearance, recording the lighting and exposure uncertainty. Keep restricted reference inputs in project research. Build review stills from the authored scene.
5. Reimport the runtime assets and measure their bounds. Rebuild from an isolated source copy with the same seed and toolchain when the generator is deterministic. Record byte equality if observed, and use dimensions and structural checks to explain any byte difference. Confirm that the served files match the checked hashes. Keep geometry checks, browser behavior and human visual approval distinct.

For a portable synthetic exercise, use the [versioned runtime fixture](runtime-glb.md#reproduce-the-runtime-character-fixture) for regeneration and reimport, and the [reference review fixture](research-driven-refinement.md#runnable-example) for contextual layers, visible leaders, nested isolation and restoration. For applications that share assets across views, use [shared-renderer views](../../full-stack-app-creation/references/multiview-review.md#shared-renderer-views).

If two GLBs with the same inputs differ in bytes, [compare imported geometry](../scripts/compare_runtime_geometry.py) independently of exporter ordering:

\`\`\`sh
blender -b --factory-startup --python-exit-code 1 --python <skill-dir>/scripts/compare_runtime_geometry.py -- <first-glb> <second-glb> --decimals 5
\`\`\`

The helper compares the multiset of world-space triangle positions at the declared rounding precision. It ignores winding and does not establish equivalence of materials, rigging, custom attributes, or different triangulations of the same surface. Run the asset contract checks for those properties.

## Capture and validation

Historical feedback, paraphrased. The surroundings should meet the same visual standard as the main model. The project replaced discontinuous ground and floating repeated shapes with a connected setting, then used a scale-appropriate camera depth range to fix flicker. Separate silhouette, detail and contextual renders made comparison possible. A screenshot also exposed SVG leaders that existed in the DOM but were hidden. The final reviewed package had 98 passing browser checks, 65 GLB checks and three byte-identical tree rebuilds. Human visual approval was pending.

| Candidate | Outcome / inputs / procedure / resources / acceptance | Weighted overlap | Basis and decision |
|---|---|---|---|
| 3d-modeling | 1 / .75 / .75 / .75 / 1 | 83.75% | Existing runtime export, authored scenes, reimport and visual gate cover most of the method. Extend with context staging, camera depth and visible leader validation. |
| full-stack-app-creation | .75 / .75 / .75 / .75 / 1 | 77.5% | Existing multiview, lifecycle, rendered tests and exact delivery cover most of the application slice. Extend with the shared-renderer option. |
| product-refinement | .5 / .75 / .5 / .25 / .5 | 50% | Its decision record informs both hosts. It leaves rendering, export and browser implementation to the hosts. |

The factors apply to each host's portion of the workflow. The two extensions follow the user's choice of targets. The shared materials are the procedures, existing Blender fixture generators, imported geometry comparator and updated browser regression. Rebuild their synthetic assets using the documented Blender, Three.js and Chromium prerequisites. The original scene source, project-specific QA, GLBs, stills and comparison photos stay with the project. Project identifiers, local paths, ports, GPU model and personal reference metadata are excluded from reusable instructions. The synthetic exercise checks the delivery and inspection behavior. The historical setting's fidelity depends on its original reference material and visual review.
