---
name: smoke-test
description: Run reusable smoke tests in isolated retained sandboxes using synthetic inputs, delivery checks, observable outputs, and retained evidence across general workflows including interactive 3D review.
---

# Interactive 3D review smoke testing

Use this skill when a 3D viewer, print-preview viewer, or browser-based model review workflow needs a reproducible smoke test. The workflow is intentionally separate from CAD correctness, slicer validation, physical fit, and load certification.

## Procedure

1. Read workspace instructions and discover Blender, a Chromium-compatible browser, Python, and the target viewer template at runtime.
2. Choose a sandbox path under the workspace `creations/` directory. Keep it separate from authored creation runs and leave it intact after testing unless the user explicitly approves cleanup.
3. Generate multiple synthetic geometric shapes and multiple lighting/shadow styles. The bundled baseline covers cube, UV sphere, cylinder, cone, torus, and icosphere with soft, left, right, rim, top, and cross lighting.
4. For each case, generate a Blender source scene, rendered PNG, GLB export, viewer files, and metadata. Keep the exact input/output relationship visible in the sandbox.
5. Serve the sandbox over HTTP. Check that the review page, GLB, metadata, CSS, and JavaScript each return HTTP 200; direct `file://` opening is not a valid test.
6. Run the browser smoke test for each case and inspect screenshots for a non-blank model, readable framing, visible shadows, and available review controls.
7. Require at least 20 passed checks before handoff. Record individual results, total count, runtime prerequisites, and any unavailable capabilities. The bundled default matrix normally produces more than 20 checks.
8. Run the reusable skill tests and syntax/entrypoint checks from an isolated copy where possible. Do not claim browser interaction if only static source checks ran.
9. Hand off the retained sandbox, result log, and representative visual evidence. Cleanup is a separate action requiring `--cleanup-approved`; never delete the sandbox automatically.

## Reusable resources

- [scripts/run_interactive_review_smoke.py](scripts/run_interactive_review_smoke.py) orchestrates the sandbox, model generation, HTTP checks, browser screenshots, result log, and cleanup boundary.
- [scripts/smoke_model_generator.py](scripts/smoke_model_generator.py) generates the synthetic Blender geometry and lighting variants.
- [scripts/launch_interactive_viewer.py](scripts/launch_interactive_viewer.py) serves a review directory over HTTP.
- [assets/interactive-review-viewer](assets/interactive-review-viewer) is the portable GLB viewer template.
- [tests/test_interactive_viewer_template.py](tests/test_interactive_viewer_template.py) checks the template contract.
- [tests/test_interactive_smoke_runner.py](tests/test_interactive_smoke_runner.py) checks the runner entrypoint and portable paths.
- [references/interactive-smoke-testing.md](references/interactive-smoke-testing.md) documents the learning goals, commands, dependencies, and cleanup boundary.
- [references/provenance.md](references/provenance.md) records the comparison, resource dispositions, feedback, and limits.

## Command

```sh
python3 <skill-dir>/scripts/run_interactive_review_smoke.py \
  --sandbox <workspace-root>/creations/smoke-test/<run-id>
```

The runner requires Blender and a Chromium-compatible browser. The viewer template loads Three.js 0.180.0 and its loader/control modules from jsDelivr at runtime, so browser network access and WebGL are external prerequisites.
