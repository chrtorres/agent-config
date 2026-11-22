# Inspect fit and deformation on exported characters

Use this pass for fitted hoods, headgear, layered clothing and expressive
faces in a runtime asset. Apply the [runtime GLB contract](runtime-glb.md)
first. Pair each reference with the detail it supports, such as a silhouette,
cloth drape, material response, eye placement, or a motion cue. Record the
asset and license for any geometry, textures or pose targets used in the
export. Keep reference photographs as design evidence unless their use in
the model is authorized.

- Inspect facial landmarks in front and profile. Inspect eyes and lids
  open and closed. For layered equipment, inspect both the opening and the
  opposite view with the item equipped. A front render can miss rear
  intersections. Keep alternate gear and soft attachments individually named.
- Choose a fit domain and record the reference frame, mesh names, sample
  bounds, viewing direction, required sample count, and clearance. Reimport
  the delivered GLB and evaluate the intended pose. Run a directional check
  from the camera side and include a known intersection to show that it fails.
- Attach wearables and soft-attachment origins to the moving rig anchor
  they follow. Exercise the parent through motion in the consumer. Measure
  the visible attachment origin against the intended anchor in the same
  coordinates. Inspect the result in a rendered frame and at direction
  changes. A supported rest pose alone leaves motion fit untested.
- Test expression deformation on the exported mesh. In the browser, observe
  the morph in its open, deformed, and restored states. Review using the
  exact GLB and pose implementation the consuming application loads.
  [Frame-aware application checks](../../full-stack-app-creation/references/playable-3d.md#check-rendered-pose-transitions)

## Reproduce the directional fit check

Requires Blender with glTF import/export and Python's bundled Blender API.
The fixture generates synthetic geometry and an expression shape key without
external media. Run each command with a fresh output directory.

```sh
blender -b --python-exit-code 1 --python <skill-dir>/tests/fixtures/create_runtime_fit.py -- --output <fitted-directory>
blender -b --python-exit-code 1 --python <skill-dir>/scripts/check_runtime_fit.py -- --asset <fitted-directory>/model.glb --contract <fitted-directory>/fit.json
blender -b --python-exit-code 1 --python <skill-dir>/tests/fixtures/create_runtime_fit.py -- --output <clipped-directory> --clipped
blender -b --python-exit-code 1 --python <skill-dir>/scripts/check_runtime_fit.py -- --asset <clipped-directory>/model.glb --contract <clipped-directory>/fit.json
```

Expect the fitted export to pass and the intentionally intersecting export
to fail with a negative margin. The report includes the tested asset hash,
sample count and misses. The contract uses Blender coordinates after GLB
import, relative to the named frame. Express lengths in meters and use a
scale-free frame so measured distances retain that unit. The direction
points toward the viewer. The scanner measures first-hit cover depth along
parallel rays on the evaluated pose. This establishes coverage of sampled
vertices in that view. For broader claims, sample additional views, poses
or surfaces and inspect the visible cloth and skin between vertices.

## Capture provenance

Comparison factors use the ordered weights from the skill capture rubric.

| Candidate | Factors | Score | Decision |
| --- | --- | ---: | --- |
| 3d-modeling | 1, .75, .75, .5, .75 | 77.5% | Extend. The runtime generator and exact-export checker already establish the delivery and reimport workflow. Research-driven refinement supplies fitting and evidence cues. Add directional clearance, rear-view inspection and the fault fixture. |
| full-stack-app-creation | .5, .5, .5, .25, .5 | 46.25% | Link the rendered-motion checks. Its playable fixture supplies runtime testing, and the Blender fit contract belongs here. |
| smoke-test | .25, .5, .25, .5, .5 | 35% | Reuse viewer smoke checks. Its synthetic shapes exercise GLB delivery and controls without evaluating fitted relationships. |

| Resource | Disposition |
| --- | --- |
| Imported geometry fit checker and genuine intersection controls | Generalized into the script above, with synthetic, source-generated GLBs and a configuration contract. |
| Authored character, studio scenes, versions, surface generation, reference imagery, source-asset licenses and rendered evidence | Retained with the original project. The shared fixture reproduces the fit method independently and needs only Blender. The original artwork and visual fidelity remain specific to that project. |
| Live pose and input replay | Captured in the linked app skill with a separate playable fixture. |

Historical feedback, paraphrased. The user wanted more realistic facial
detail and movement and asked for independent regression review. A close
front view appeared fitted while the rear of the head intersected the hood.
The corrected export passed the rear directional sample. Open and closed
facial views, live cloth-anchor checks, and a hash-matched browser review
provided additional evidence. Those observations establish the checked
poses and views.

Generalized fields include model and attachment names, geometry units and
thresholds, build and evidence paths, and renderer and application identity.

## Soft attachments in motion

A static or rest-pose fit does not cover cloth that moves. In the originating run, a scarf tail hung cleanly at rest but clipped through the body while running. Its collider was a fixed vertical capsule that was narrower than the cape and did not follow the running lean or the bank into turns.

- Measure the collider from the delivered GLB. For each height band in a bone's rest frame, record back depth, half-width and front depth. Add the ribbon half-thickness and edge reach as clearance. Use one table per bone that covers a height range, such as chest and pelvis.
- Collide in the bone's local frame, using the inverse of its world matrix after animation, so the collider follows lean, bank, crouch and runtime scale.
- Use the particle's previous position to choose the exit side, so fast cloth exits behind rather than through the chest. Seat the root on the outside of the collar instead of at an anchor buried in the neck mesh.
- Test standing, sprint lean, and a banked turn together. Measure penetration against the bare silhouette, with no clearance, in the bone frame. Include faults that must fail: a narrow fixed capsule and an upright collider that ignores the bone.

Run the dependency-free [cloth collider example](../assets/cloth-collider-example/README.md) with `node --test test-cloth-collider.mjs`. Its reference magnitudes are 0 cm for the bone-attached profile, about 14 cm for the narrow capsule and about 7 cm for the upright collider. Then confirm the fix visually in the running app during a sprint and a turn. To carry the same motion to panels, sleeves and tied hair, see [one cloth style across a whole outfit](runtime-outfit-cloth.md).

Capture note. The incoming workflow scored 1, .75, .5, .5, .75, which is 68.75%. The existing fit pass covers moving anchors and directional clearance but not simulated cloth. The user directed extending this skill, so the method was added here and not as a separate skill. Historical feedback, paraphrased: the user reported that the scarf clipped through the body when running. The bone-attached measured profile removed the clipping in the originating game's test, and the old capsule failed it. Generalized fields include character, bone and anchor names, measured rows and project paths.
