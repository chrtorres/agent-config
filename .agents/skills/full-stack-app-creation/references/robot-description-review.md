# Browser checks for a robot-description review

Use this for an interactive review that shows a robot description: a multipart GLB with frame and collision presets and a joint-exercise clip. The modeling side is in [../../3d-modeling/references/robot-description.md](../../3d-modeling/references/robot-description.md). Serve the review over HTTP and drive a real browser; static renders do not exercise the clip or presets.

## Extend the shared harness, don't fork it

Load the 3d-modeling multipart harness ([check_multipart_viewer.py](../../3d-modeling/tests/check_multipart_viewer.py)) as a module, keep its `perform_checks`, and wrap it with project checks. Before relying on it, confirm its selectors match the current viewer template (part key list, leader lines, clip option labels); the harness and template can drift, and a selector mismatch reads as a product failure.

## Checks to add

1. **Callouts.** On the narrow layout: one visible callout per part, one key entry and one leader line per part. Clicking a callout isolates exactly one mesh, and reassembly hides all callouts and the key.
2. **Presets.** Read `metadata.json`. The View options equal the `modes` keys in order. For each preset, the set of visible nodes equals its members exactly, after Three.js node-name sanitization (`PropertyBinding.sanitizeNodeName`). Screenshot each and assert the screenshot is not blank.
3. **Clip.** The clip selector exposes one labelled clip (for example `"<name> (<seconds> s)"`). Scrub with the time slider's `input` event to keyed times and read the joint state from the scene graph:
   - revolute: angle from the node quaternion, `2·acos(|w|)`, within the keyed window;
   - prismatic: node translation delta against rest, along the joint axis, to about 0.2 mm;
   - scrub back to 0 and confirm rest.
4. **Pause and explode.** Explode while the clip is paused mid-motion, then reassemble; node transforms must return exactly to the paused pose, not the rest pose.
5. **Reduced motion.** With `prefers-reduced-motion: reduce`, auto-play stays off; switch to `no-preference` before clip checks.

Retain screenshots (each preset, a mid-clip pose, labelled desktop view) and the numbered check list with the evidence. Keep failed attempts beside the passing rerun.
