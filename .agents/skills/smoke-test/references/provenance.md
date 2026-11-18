# Interactive review smoke-test skill provenance

## Comparison and routing

The user explicitly requested that the generalized smoke-test workflow be captured as a reusable skill. Candidate comparison before capture:

| Candidate | Outcome/user journey | Scope/inputs | Procedure | Resources/dependencies | Validation | Score | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `3d-modeling` | 0.75 | 0.75 | 0.50 | 0.75 | 0.75 | 66.25% | Keep integration, but create this focused skill per explicit direction |
| `full-stack-app-creation` | 0.50 | 0.25 | 0.50 | 0.50 | 0.75 | 47.50% | Reject: broader application workflow |
| `live-app-recreation` | 0.50 | 0.50 | 0.50 | 0.50 | 0.75 | 53.75% | Reject: app recreation is not model-review QA |

The focused smoke-test workflow is below the normal 75% threshold against `3d-modeling`, so a separate skill is appropriate. It remains linked conceptually and operationally from `3d-modeling`, whose required review section uses the same procedure.

## Resource disposition

- Bundled: viewer HTML/CSS/JavaScript, synthetic Blender generator, HTTP launcher, smoke runner, smoke tests, and generalized procedure.
- Generalized: task-specific sphere names, dimensions, host paths, ports, output names, and metadata were replaced with caller parameters or synthetic shape/style values.
- Regenerated: `.blend`, `.glb`, `.png`, browser screenshots, logs, and result manifests are generated per sandbox run and are not bundled here.
- External prerequisites: Blender, Chromium-compatible browser, Python, WebGL, and network access to the pinned Three.js CDN modules.
- Deliberately excluded: slicer, mesh-repair, finite-element analysis, CAD editing, physical printing, load certification, credentials, caches, and active server state.

## Feedback trace

User request: capture the generalized smoke test with `skill-add` as a reusable procedure.

Response: created this standalone skill, preserved the `3d-modeling` integration, bundled the runnable resource set, and retained generated evidence outside the skill.

Observed validation: the generalized runner produced 62 passed checks across six shapes and six shadow styles, including browser-rendered screenshots.

Remaining limit: a passing interactive smoke test demonstrates viewer delivery and rendering only; it does not prove model correctness, printability, strength, or load capacity.
