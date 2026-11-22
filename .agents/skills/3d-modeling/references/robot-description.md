# Robot description from a multipart reconstruction

Use this when a photo-based or research-driven multipart model must become a machine-readable robot description: frames, joints, sensors, mass properties, collision geometry and a simulator-loadable URDF, with every value traced to a source or flagged as an estimate. Start from a model that already passes the multipart review in [photo-based-refinement.md](photo-based-refinement.md). The approval gate in the main skill still applies; a valid URDF is not hardware calibration.

## 1. Fix the frame before touching geometry

- Adopt ROS REP-103/105 unless the caller's stack says otherwise: +X forward, +Y left, +Z up, metres and radians. Put `base_footprint` on the floor under the drive-axle midpoint and `base_link` on the axle (`z = wheel radius`).
- Write the construction-to-robot transform once, as a matrix in the generator (for example `Scale(mm→m) @ RotZ(θ) @ Translate(-axle)`), and bake every part through it. Do not let per-part code reason about handedness.
- **Re-check left/right against a primary source** (manual anatomy figures, underside photos). Mirrored construction axes silently swap "Left" and "Right" names and sensor sides. Record the source that settles each side.

## 2. Pivots, joints and links

- Give every moving part its object origin **on its joint axis** in the robot frame. The Blender object, the GLB node and the URDF joint must share that pivot; snap pivots to ~1e-7 m so exact-equality checks do not fail on float noise.
- Keep a single table in the generator mapping each part to a URDF link (rigid parts aggregate into one link) and each link to a joint: type, axis, parent, limits, and the source or estimate for each value. Generate the URDF, per-link meshes (one Collada/STL per link in the link frame) and a `robot_spec.json` from that table, never by hand.
- Model compound passive joints as separate links (for example a caster swivel then a caster wheel). Model contact travel (bumper, lidar cover) as small prismatic joints with estimated limits.
- Make sensor frames fixed joints with an explicit convention (state which axis faces outward). Mark unverified placements (an IMU at the board centre, say) as assumptions in the spec.

## 3. Mass, inertia and contact

- Take total mass from the best available source; assign part masses as labelled estimates, give the chassis the remainder, and assert the total.
- Compute link inertials from a composite of box (or cylinder) approximations with parallel-axis terms. Check that every tensor is positive definite and obeys the triangle inequality.
- State a centre-of-mass assumption explicitly (for example "COM N mm ahead of the axle"), place the remainder mass to achieve it, and assert the remainder COM is physically plausible. Document a measurement that replaces it (a scale under the caster gives `x_com = W_caster / W_total × wheelbase`).
- Make wheels touch `z = 0`: tread lugs or chamfers move the lowest vertex; measure the mesh minimum rather than trusting the nominal radius.
- Collision geometry: simple primitives per link (cylinder body, cylinder wheels, sphere caster), exported to the viewer as an optional preset.

## 4. Physical consistency

Run [scripts/check_interference.py](../scripts/check_interference.py) inside Blender on the saved `.blend`:

```sh
blender -b <model.blend> --python-exit-code 1 --python <skill>/scripts/check_interference.py -- \
  --allow <allowlist.json> --poses <joint-poses.json> --report <out.json> --strict
```

- Allowlist entries are `{"pair": [a, b], "reason": "..."}` for designed overlaps only (flexible bristles through a guard). Stale entries are reported.
- Pose files are `[{"name": ..., "moves": [{"node": ..., "rotate_deg": [x,y,z], "translate_m": [x,y,z], "about": <other node>}]}]`. Sweep every joint at several points across its full range, including limits. A lid that only clears at rest is a common hidden failure; so is a bumper at full travel hitting an internal deck.
- Mark viewer-only guide objects with a custom property (default `review_guide`, set with `--skip-property`) so they are not tested as parts.

## 5. Viewer additions

- Frame triads with origins **on** each frame (not the world origin), a footprint ring and collision primitives as separate named nodes, flagged as guides.
- Keyframe one exercise clip that moves every joint across its range. Blender exports one glTF animation per object; merge them with [scripts/merge_glb_animations.py](../scripts/merge_glb_animations.py) `<model.glb> "<clip name>"`.
- Add metadata `modes` presets: assembled, a configuration without removable accessories, sensor/joint frames over kinematic context parts, and collision primitives.
- If the generator renders posed stills after keying the clip, detach actions first, or the keyframes override the pose.
- Browser checks for presets and clip scrubbing are in [../../full-stack-app-creation/references/robot-description-review.md](../../full-stack-app-creation/references/robot-description-review.md).

## 6. Robot data checks

- [scripts/check_urdf.py](../scripts/check_urdf.py) `<urdf> --package-root <pkg> --expect <expect.json>`: tree, joint types, axes, limits, mesh resolution, inertia validity, plus optional total mass, sensor-frame FK poses (compared as rotation matrices, 1e-6), wheel/caster floor contact and COM inside the support polygon. See its docstring for the expect format.
- Add project checks on top: GLB node pivots equal URDF FK, frame guide positions equal FK, the clip exists, presets list existing nodes. Keep spec rotations at ≥ 12 decimals; 6-decimal rpy fails 1e-6 orientation checks.
- Load with an independent parser (yourdfpy in a scratch venv, with trimesh and pycollada for DAE meshes) and compare its envelope and FK with Blender's.
- Keep photo landmark checks (`compare_landmarks.py`) so robot-frame edits do not drift calibrated features.

## 7. Regeneration and fault injection

- Rebuild from an isolated copy of the source. Text exports (URDF, spec, metadata, geometry JSON) should be byte-identical; compare binary exports by decoded content with [scripts/compare_glb_exports.py](../scripts/compare_glb_exports.py). DAE files differ in timestamps and UVs; compare position arrays and indices. Use a correct canonical sort; a weak one creates false mismatches.
- Inject at least one mutation per check family into a copy (raise a wheel 1 mm, flip a sensor yaw, move a landmark part, empty the allowlist, over-travel a joint, change one mass). **Assert each replacement actually applied** before running the check; an unmatched sed gives a false pass.

## 8. Package and hand off

- A ROS 2 `ament_cmake` description package: `package.xml` (placeholder maintainer), `CMakeLists.txt` installing `urdf meshes launch`, a `display.launch.py` with robot_state_publisher, joint_state_publisher_gui and RViz, and a README.
- In the README, separate values into sourced, photo-calibrated and estimated, and give a calibration procedure for each estimate (wheel radius/track by straight-line and spin tests, laser height against a wall scan, COM by scale, joint travels).
- Say plainly whether the package was built or opened in RViz. Suspension, compliance and sensor characteristics that are not modelled stay listed as limits.
