# Synthetic model inspection example

## Outcome

A reviewer switches between the assembly and a component while retaining the same orientation.

## Baseline

Switching the selected component placed the camera inside the mesh. Reproduced with a synthetic two-box assembly.

## Decisions

Preserve orbit orientation and refit the selected bounds. Test both narrow and wide viewports.

## Validation

Observe rendered component pixels and camera positions. Force an invalid selected bound and confirm that the framing test fails.

## Handoff

Retain the fitted render and the isolated rendering test. The sample geometry is synthetic.
