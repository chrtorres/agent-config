# Versioned 3D review application

Use this pattern when one local application must present successive model revisions, planning data and a standalone multipart reviewer without hiding engineering uncertainty.

## Data and lifecycle contract

1. Discover revision directories from a caller-supplied project root. Include a revision only when its checks, review metadata and GLB all exist. Resolve duplicate slugs deterministically and keep private authoring files outside the served route allowlist.
2. Return a compact draft descriptor containing the stable slug, version, title, summary, checks, part metadata, node mapping and review URLs. Serve the exact GLB bytes referenced by that descriptor. Hash the file delivered over HTTP and compare it with the reviewed artifact during handoff.
3. Choose the initial revision after loading the index. Honor a saved slug only while it still exists. Otherwise choose the last complete revision in the declared ordering. Store the choice as a convenience. Keep the server's source of truth independent from browser storage.
4. Render partial engineering data defensively. Empty structural arrays, `null` split counts and missing optional metrics have explicit pending states. Carry `estimated`, `assumed` and `pending design` labels from the model checks into visible UI copy.
5. Link inventory entries to stable GLB node names. Verify list-to-model highlighting and model-to-list picking. Exercise explode and exact reassembly in the integrated app, then run the standalone multipart harness against the same review package.
6. Browser-test the complete discovered index. Open every standalone review and compare its rendered part-key and picker counts with metadata. Also test fresh-session default selection, saved-selection reload, keyboard revision switching, narrow layout, error responses and persistence conflicts when the app edits planning data.
7. Give local preview processes an owner and lifecycle. A test-owned server stops in `finally`. A retained handoff preview has an explicit start command and stop command in task evidence. Stop it during cleanup and verify the documented launch path from a clean state.
8. Package handoff evidence by outcome. Keep a concise test summary, representative settled screenshots, runtime versions and a hash manifest. Exclude temporary browser profiles, PIDs, caches, copied dependency trees and superseded isolated builds after the user authorizes cleanup.

The browser application's checks establish navigation, rendering, selection and state restoration. Geometry validity, attachment design, fabrication and physical performance remain the modeling workflow's responsibility. See [versioned concept refinement and handoff](../../3d-modeling/references/versioned-concept-handoff.md).

## Capture decision and resources

The pre-update `full-stack-app-creation` skill scored 80% against the incoming application workflow using factors `1, .75, .75, .5, 1`. It already covered the local vertical slice, persistence, browser interaction, isolated evidence and runnable delivery. The missing decisions were complete-revision discovery, saved-selection fallback, uncertainty-aware metric rendering, exact GLB delivery and preview cleanup. The compatible existing skill was extended under the user's explicit direction.

Reuse the 3D skill's browser viewer, multipart harness and synthetic smoke runner. Reuse this skill's live-state browser QA and isolated-evidence guidance. The originating planner source, real model files, inventory and screenshots remain project artifacts because they encode task-specific hardware and design decisions.

Historical feedback, paraphrased. The user asked to iterate until the visual result was as close as practical, maintain a running handoff and clean the workspace for transfer. The app response exposed all complete revisions, opened the latest complete one for fresh sessions, preserved saved valid choices, labeled unfinished engineering and validated both integrated and standalone review paths.

Generalized categories include absolute paths, usernames, project names, draft slugs, ports, service names, hardware identities, measurements, run IDs and timestamps. External prerequisites are a Python or equivalent local server runtime, a browser with WebGL, the reviewed GLBs and the model-review viewer dependencies.
