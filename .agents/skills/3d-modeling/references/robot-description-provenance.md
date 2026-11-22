# Robot description capture: comparison, resources and feedback

## Comparison

The user named both target skills, which takes precedence over the score. The scores are recorded anyway.

| Candidate | Overlap | Decision |
|---|---|---|
| 3d-modeling | High (about 80%). The skill already covers the photo-based multipart reconstruction, named pivots, the GLB review viewer, the multipart harness and the landmark checks. New material: frame baking, URDF/spec generation, inertia/COM/contact, the BVH pose sweep, clip merging and the robot-data checks. | Extend: new reference and four scripts |
| full-stack-app-creation | Low for the modeling work. The browser-verification method applies, but the preset and clip-scrub assertions are new. | Extend: one browser-check reference, as directed |
| product-refinement | Covers the decision record and baseline only | Linked, not changed |

## Resource disposition

| Resource from the source run | Disposition |
|---|---|
| BVH interference audit | **Bundled** as `scripts/check_interference.py`. The guide property name is now a parameter. |
| GLB animation merge (a function in the generator) | **Bundled** as `scripts/merge_glb_animations.py` |
| Regeneration export comparison | **Generalized** into `scripts/compare_glb_exports.py`. The DAE comparison is described in the reference. |
| Project robot check (125 checks) | **Generalized** into `scripts/check_urdf.py` with an expect file. Project-only checks (GLB pivots against FK, presets) are described instead. |
| Project generator (~1300 lines), meshes, renders, blend file | **Excluded.** They are project-specific, and the procedure is in `robot-description.md`. |
| Owner manual and retailer sources | **Excluded.** The license is unknown and the material is product-specific. |
| Browser wrapper | **Described** in `full-stack-app-creation/references/robot-description-review.md` |
| Synthetic test URDF and expect file | **New**, in `tests/fixtures/robot-description/` |

**Generalized values:** product, model and project names; workspace paths; part names; dimensions, masses and travel values; port numbers.

## Feedback (paraphrased)

- The user said detail and precision matter for an autonomous-agent robotics project. Response: every value is tagged as sourced or estimated, with calibration procedures; checks compare FK, pivots and contact to 1e-6 m, or to 1e-4 m for contact.
- The user gave full autonomy to plan and complete the work. Response: no change to the approval gate. The model is still pending user review, and no printing was done.

## Historical results (examples, not current passes)

The source run's results:
- 125/125 robot checks
- 0 unexpected interferences across 21 poses
- 9/9 landmarks
- 147/147 browser checks
- 6/6 mutations detected

During capture, the bundled `check_interference.py`, `check_urdf.py` and `compare_glb_exports.py` were re-run against that run's outputs. The results matched: 0 unexpected interferences across 21 poses, 69/69 generic checks, and all comparisons MATCH.
