# One cloth style across a whole outfit

Use this after one soft attachment works (see [soft attachments in motion](runtime-character-fit.md#soft-attachments-in-motion)) and the user wants the rest of the costume to move the same way. Use it also when a garment, hairstyle or fit change alters the silhouette that the cloth collides with.

## Classify every part that should move

Give each part the cheapest model that produces the motion people notice:

| Part | Runtime model | Asset contract |
| --- | --- | --- |
| Long free ends (scarf tails, sash ends, ponytail, ribbons) | World-space Verlet ribbon. Collides with the measured silhouette. | Named anchor node at the root, plus the material name the ribbon reuses. Remove any rigid copy of the free end from the mesh. |
| Short hanging panels (skirt tassets, coat tails) | Damped pendulum per panel. Tilts against body acceleration and lags yaw. | One pivot per panel at its belt line. |
| Garment pieces around a limb (wide sleeves, tabards) | One hem particle per piece, pulled back toward its rest shape and limited to a cone (`stepHem`). The pivot turns toward the hem. | Pivot just under the joint the piece hangs from, with the geometry parented to it. |
| Hair tied at the root | Ribbon with a spring toward a raked rest line (`pullTowardRestLine`). Its ceiling is any hat or hood above it. | Anchor at the back of the knot. Draw each lock as two crossed ribbons so it keeps volume edge-on. |

Update all parts after the animation pose for the frame. Use one fixed-step accumulator. Hide every runtime part when its anchor is missing, for example when a fallback model loads.

## Modeling changes that feed the simulation

- After any fit change (slimmer garments, removed layers, new hair), re-measure the collider with [measure_body_profile.py](../scripts/measure_body_profile.py). Exclude limbs, hats, scabbards and swinging panels. The script samples along edges because lofted garments have rings several centimetres apart. In the originating run, sampling vertices only left three chest bands empty. Keep the measured rows beside the asset, and give hair its own smaller clearance: a hair lock is thinner than a silk ribbon, and silk clearance leaves the hair floating centimetres off the skull.
- Read the costume at game distance before changing geometry. A coarse woven normal map on a dark robe read as chain mail. The user called it armor. Tiling the weave finer (Mapping node, exported as `KHR_texture_transform`) and softening its normal strength made it read as cloth.
- When a tube sleeve starts above the rounded shoulder cap, its flat top reads as a shoulder plate. Start the sleeve just below the cap.
- Remove hidden interior parts that block new geometry. A hat's inner headband intersected a new crown knot and the tail leaving it.
- Keep node names that runtime code and tests already look up, even when the contents change (a head wrap replaced by hair). Record the reason in the source.

## Constraints that keep the motion believable

- **Ceilings must extend past their edge.** A tail anchored under a wide hat swings around the brim during a leap and a stop, then rises above the hat. Clamp to the hat's underside inside the brim and to brim height beyond it, out to roughly the tail's length (`hatCeiling`).
- **Cone limits keep a limb covered.** Size the cone from the hem's clearance around the limb, not from how dramatic the swing looks.
- **Body velocity drives the drag.** Cloth streams behind a sprint because drag acts on world velocity. Do not add a separate "trail" animation.

## Reproduce

From [the cloth collider example](../assets/cloth-collider-example/README.md), run `node --test`. `test-outfit-cloth.mjs` covers a sleeve hem that hangs, droops under a raised arm, trails and settles. It also covers a tied tail in a sprint, leap and stop under a conical hat. In the reference run, a ceiling that stopped at the brim let the tail rise 0.285 m above the brim. The tie alone still allowed 0.095 m, and the extended ceiling held it at 0. `tests/test_measure_body_profile.py` builds a synthetic lofted body in Blender. It checks that bands between the rings are present, that excluded subtrees are ignored, and that the root scale is divided out.

Confirm the result in the running app with close views: standing front, side and rear, sprint, turn, leap, the first frames after a stop, settled, and an attack with a raised arm. [Playable 3D close inspection](../../full-stack-app-creation/references/playable-3d.md#outfit-cloth-and-close-inspection) shows how to hold a camera near the character without changing the game camera.

## Capture decision and provenance

The user named this skill as a target. The incoming workflow scored 1, 1, .75, .5, .75 (25 + 15 + 26.25 + 7.5 + 7.5 = 81.25%) against 3d-modeling. The runtime GLB contract, the character fit pass and the cloth collider example already covered the asset side and one ribbon. Panels, sleeves, tied hair, the hat ceiling and silhouette re-measurement were new, so the skill was extended.

Historical feedback and responses, paraphrased:

- The user liked the scarf and skirt physics and wanted the rest of the outfit to match. Response: the hair, sash and sleeves were classified and moved onto the same fixed-step loop. Observed: unit tests kept every particle outside the measured body through standing, sprint, bank and leap. In-game captures showed trailing and settling. Limit: the sleeve is one rigid piece that swings; it does not fold.
- The user asked for the armor to fit tighter. Response: the bulky shoulder layers were removed, the kimono, belt, trousers and skirt were narrowed by about 10 %, the weave was tiled finer, and the collider was re-measured. Observed: the scarf now hangs closer to the back without clipping.
- The user asked for a tattered kimono and long hair in a knot. Response: torn sleeves on shoulder pivots, combed hair into a bound knot, and a runtime tail. Observed in captures: the first stop sent the hair over the hat, which led to the extended ceiling and the tie spring.

Generalized fields include character, node and material names, measured rows, project and evidence paths, ports and hashes. The originating game, its licensed head topology and its evidence stay with that project.
