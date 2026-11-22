# Multiview review architecture

Use a small shell when combining existing review engines that own independent rendering and control state. Declare view IDs, labels, sources, default selection, and any initial inspection mode in a build manifest. Publish only the browser fields the shell needs. Preserve each package's relative assets and downloads.

- Load each scene on its first visit. Preserve the size of its retained canvas and make invisible panels unfocusable. Use fragment navigation, keyboard tab switching and an independent loading state in each view.
- Let the host signal visibility and each scene manage its clock. A same-origin child verifies the sender before accepting an activity signal. Clear the prior frame timestamp when inactive to avoid a jump on resumption. Separate an explicitly paused scene from one that was playing when hidden.
- Drive verification through the assembled HTTP package. Observe an actual frame or state transition before asserting. Exercise initial, deep-linked, keyboard, history and portrait entry. Verify that nested geometry selection survives switching, reassembly restores transforms, and one missing asset leaves the other views usable.
- Record which dependencies and model bytes are delivered, and preserve evidence in an isolated run. Separate application integration checks from fidelity or shared-clock claims.

The sibling [combined review workflow](../../3d-modeling/references/combined-review-workspaces.md) includes a packager, shell, custom view adapter, time-bounded trace sampler recipe, synthetic model generators and browser harness. See [capture provenance](../../3d-modeling/references/combined-review-provenance.md) for the resource inventory.

## Shared renderer views

Use one renderer when related views share a scene or substantial assets. Key reusable assets by identity and keep camera, selection and inspection state scoped to the view and selected specimen. Refit when an inspection changes bounds, and restore the assembled pose and camera when reassembling. Stop the simulation clock on inactive views and reset the frame timestamp on resume. When a light and its casters are static, reuse the shadow map and invalidate it when geometry, visibility or animation changes.

Make only the current request eligible to reveal a newly loaded asset. Cancel obsolete fetches or ignore their completions, keep retry local to the failed view, and provide a still if live 3D cannot start. Test missing and malformed assets through the served application, then restore the resource and retry in the same view. Verify that switching views preserves independent state and keeps renderer resources bounded.

Capture a settled frame and assert observable geometry and overlay state. A line can exist inside a hidden SVG, so check whether its parent is visible and its stroke and endpoints can produce a line. In a local fixture, hide the overlay while leaving its children in place to make sure the assertion fails. Inspect the screenshot to check the line placement. Compare the actual bytes returned by the server and downloaded by the browser with the reviewed package.

Record the WebGL backend used. Software rendering can validate compatibility and render behavior. Use a confirmed hardware renderer for hardware performance measurements and label timings by backend. The [reference review fixture](../../3d-modeling/references/research-driven-refinement.md#runnable-example) reproduces the overlay and isolation checks. The [context and inspection capture](../../3d-modeling/references/context-and-inspection.md#capture-and-validation) records the workflow evidence.
