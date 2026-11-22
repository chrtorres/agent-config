# Cloth collider example

Run `node --test` from this directory (Node.js 20 or later, no dependencies). It runs `test-cloth-collider.mjs` and `test-outfit-cloth.mjs`.

`cloth-collider.mjs` simulates a soft attachment (scarf tail, sash, ribbon) as a Verlet chain with linear air drag, length constraints and a body collider. The collider is a per-height ellipse table, `[height, back, half-width, front]`, measured from the exported mesh in the frame of the bone it follows. Collision runs in that bone's local frame, so it follows lean, bank and crouch. The previous particle position chooses the exit side, so fast cloth cannot tunnel to the front of the chest.

The silhouette rows in the test are synthetic. For a real character, sample the delivered GLB at each height band in the bone's rest frame and add a clearance (ribbon half-thickness plus edge reach). Use one table per bone that covers a height range, such as chest above the waist and pelvis below.

The tests reproduce the defect that motivated this example. A tail that hung cleanly at rest sank into the body when running. Expected magnitudes from the reference run:

| Collider | Deepest penetration |
| --- | ---: |
| Measured profile, bone-attached | 0 cm |
| Fixed narrow capsule | about 14 cm |
| Measured profile, upright world frame (ignores lean and bank) | about 7 cm |

In a renderer, read the bone's world matrix after the animation update, invert it once per frame, and step the chain at a fixed rate with a bounded accumulator. Seat the root on the outside of the collar rather than at an anchor buried in the neck mesh.

## Whole-outfit helpers

`outfit-cloth.mjs` adds the parts that extend the same style across a costume:

- `stepHem`: a sleeve-like piece swinging from a pivot within a cone.
- `pullTowardRestLine`: a tie spring for a tail that is tied at its root.
- `hatCeiling` and `clampUnderCeiling`: a hat underside that continues past the brim.

`test-outfit-cloth.mjs` reproduces the hat fault from a sprint, leap and stop. In the reference run, a ceiling that ended at the brim let the tail rise 0.285 m above the brim. The tie alone still allowed 0.095 m, and the extended ceiling held it at 0. See [one cloth style across a whole outfit](../../references/runtime-outfit-cloth.md).
