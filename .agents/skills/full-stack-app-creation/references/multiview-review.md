# Multiview review architecture

Use a small shell when combining existing review engines that own independent rendering and control state. Declare view IDs, labels, sources, default selection, and any initial inspection mode in a build manifest. Publish only the browser fields the shell needs. Preserve each package's relative assets and downloads.

- Load each scene on its first visit. Preserve the size of its retained canvas and make invisible panels unfocusable. Use fragment navigation, keyboard tab switching and an independent loading state in each view.
- Let the host signal visibility and each scene manage its clock. A same-origin child verifies the sender before accepting an activity signal. Clear the prior frame timestamp when inactive to avoid a jump on resumption. Separate an explicitly paused scene from one that was playing when hidden.
- Drive verification through the assembled HTTP package. Observe an actual frame or state transition before asserting. Exercise initial, deep-linked, keyboard, history and portrait entry. Verify that nested geometry selection survives switching, reassembly restores transforms, and one missing asset leaves the other views usable.
- Record which dependencies and model bytes are delivered, and preserve evidence in an isolated run. Separate application integration checks from fidelity or shared-clock claims.

The sibling [combined review workflow](../../3d-modeling/references/combined-review-workspaces.md) includes a packager, shell, custom view adapter, time-bounded trace sampler recipe, synthetic model generators and browser harness. See [capture provenance](../../3d-modeling/references/combined-review-provenance.md) for the resource inventory.
