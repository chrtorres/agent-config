# Interactive viewer capture record

## Routing decision

The user explicitly requested extending `3d-modeling`, so the viewer capability is added there as an optional review mode rather than created as a separate skill.

Before this update, the weighted comparison was:

| Candidate | Outcome/user journey (25) | Scope/inputs (15) | Procedure (35) | Resources/dependencies (15) | Validation (10) | Score | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `3d-modeling` | 0.75 | 0.75 | 0.50 | 0.25 | 0.50 | 56.25% | Extend by explicit user direction; add optional viewer mode |
| `full-stack-app-creation` | 0.50 | 0.25 | 0.50 | 0.50 | 0.75 | 47.50% | Reject: broader application scope, not 3D-modeling-specific |
| `live-app-recreation` | 0.50 | 0.25 | 0.50 | 0.50 | 0.75 | 47.50% | Reject: focused on app recreation, not model review |

The numerical score for `3d-modeling` is below the normal 75% extension threshold, but the user's explicit target takes precedence. The scopes are compatible because the viewer is optional, remains a review aid, and does not replace the existing Blender/print approval gates.

The generalized smoke-test procedure was subsequently captured as the standalone [`smoke-test`](../../smoke-test/SKILL.md) skill, while this skill retains the required integration for modeling workflows.

## Captured resources

- `assets/interactive-review-viewer/`: generalized HTML/CSS/JS viewer template, synthetic metadata contract, and runtime notes.
- `scripts/launch_interactive_viewer.py`: configurable local HTTP launcher with directory and port parameters.
- `scripts/smoke_model_generator.py`: portable synthetic Blender geometry and shadow generator.
- `scripts/run_interactive_review_smoke.py`: generalized multi-shape, multi-shadow browser smoke runner with explicit cleanup boundary.
- `tests/test_interactive_viewer_template.py`: structural and privacy-oriented template checks.
- `tests/test_interactive_smoke_runner.py`: entrypoint and portability checks for the generalized runner.
- `references/interactive-viewer.md`: this routing and provenance record.

## Generalization and exclusions

- Task-specific model files, screenshots, server PID files, hostnames, ports, and metadata values were not copied into the skill.
- The template expects caller-supplied `model.glb` and `metadata.json` in the current version's review directory.
- Three.js 0.180.0 and its examples modules are loaded from jsDelivr at runtime; network access and WebGL are external prerequisites.
- The template does not include a mesh validator, slicer, finite-element solver, CAD editor, or load-certification logic.
- The viewer is now a required review artifact for every new or revised modeling workflow; the smoke-test sandbox remains task evidence and is not bundled into the shared skill.

## Required smoke-test contract

Each viewer workflow must run at least 20 checks in an isolated sandbox before handoff. The checks must include multiple geometry types and multiple lighting/shadow setups, and must verify both delivery and observable browser rendering. The sandbox is retained until the user explicitly approves cleanup.

## Feedback trace

User request/paraphrase: provide a minimal interactive environment to rotate the 3D object and understand the design.

Implementation response: packaged a browser-local GLB viewer with orbit/zoom/pan, reset, auto-rotate, wireframe inspection, fit-aware camera limits, review metadata, and explicit approval/engineering-limit messaging.

Observed outcome: the version-003 viewer loaded the GLB in Chrome headless, rendered a non-blank model screenshot, and returned HTTP 200 for the viewer and model asset.

Remaining limit: browser interaction and GLB rendering are review evidence only; they do not establish printability, physical fit, strength, or load capacity.
