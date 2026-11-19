# Animated figure review

1. Choose representative motions and measurable outcomes. Record units, axes, root, joints, contacts, phase relationships, timing, and intended repetition. For observed motion, cite the applicable figure or recording and document where you infer scale, timings, or hidden degrees of freedom. Keep trajectory, articulation, and visual review separate measurements.
2. Start with a rest asset and record mesh, root, pivot, and binding identities. Assign rigid links to pivots or skin deformable surfaces with normalized weights. Pose in local joint coordinates. Keep root travel separate from joint articulation so speed, direction, and deformation can be measured independently. Validate attachment drift or contact at representative poses.
3. Evaluate a time-to-channel function at a fixed rate, including the initial and final keys. Use stable radians/meters and shortest-arc quaternion interpolation when supplied with quaternions. For cyclic motion, check endpoint poses and adjacent velocities. A segment that intentionally changes pose can play once. For traveling loops, make an explicit decision about the root path and return behavior.
4. Bake named Blender actions and export only the needed geometry, rig and actions. Review exact exported bytes. Check channel movement, clip durations, and required seams numerically. Review pivots, silhouette and deformation through rendered poses at critical times, including alternate axes and slow playback. Apply the negative case before trusting a seam check.
5. Supply the same GLB and clip labels to the [portable viewer](../assets/interactive-review-viewer/README.md#animated-models). Declare a unique follow node only when camera tracking helps. Preserve static and exploded inspection where relevant. Record browser, asset hash, representative screenshots, assumptions, scope, and approval state.

## Reproduce from the bundled resources

Requires Blender 4.5 LTS, Python 3.10+, Node.js with Playwright and Chromium, and a WebGL-capable browser. For offline packaging, obtain the pinned Three.js 0.180.0 package with `npm pack three@0.180.0` and use its extracted directory.

```sh
blender -b --python-exit-code 1 --python <skill-dir>/scripts/create_motion_fixture.py -- \
  --kind flexible --output <flexible-fixture-directory>
blender -b --python-exit-code 1 --python <skill-dir>/scripts/create_motion_fixture.py -- \
  --kind articulated --output <articulated-fixture-directory>
python3 <skill-dir>/scripts/check_motion_glb.py <flexible-fixture-directory>/fixture.glb \
  --loop Traverse --moving Traverse "Travel root" translation
python3 <skill-dir>/scripts/check_motion_glb.py <articulated-fixture-directory>/fixture.glb \
  --loop Oscillate --moving Swing Hinge rotation
```

Run the hinge check again with `--loop Swing`. The intentional one-shot should fail because its endpoints differ. Package both fixtures with the same command pattern.

```sh
python3 <skill-dir>/scripts/prepare_reference_review.py <fixture-directory>/fixture.glb \
  --metadata <fixture-directory>/metadata.json --three-dir <three-package-directory> \
  --output <served-directory>/<kind> --no-screenshot
python3 <skill-dir>/scripts/launch_interactive_viewer.py --directory <served-directory> --port <port>
node <skill-dir>/tests/check_motion_review.mjs <serve-url> <evidence-directory> <playwright-module>
```

Run preparation for both `flexible` and `articulated` before the browser check. For your own rig, use `bake_action(owner, name, duration, fps, evaluate)` from the fixture script. The sampler supplies a fixed mapping of Blender RNA data path and component index to finite values at each time in seconds. Initialize all driven channels and author continuous Euler samples or consistent quaternion signs. Configure semantic distances, axes, expression laws and tolerances in your caller.

The checker covers ordinary GLBs with dense float32 animation accessors and supports sign-equivalent quaternion endpoints. Endpoint equality by itself cannot establish derivative continuity, anatomical fidelity, fluid or contact physics, or motion-capture correspondence.

[Capture provenance and resource inventory](animated-figure-provenance.md)
