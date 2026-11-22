# Real-world physics baseline for a playable character

Use this mode when the user asks for movement that "reflects real life" (collision, climbing, speed, velocity, turning) in a browser game or simulation, usually as a baseline they will tune up from. Apply [playable 3D regression and delivery](playable-3d.md) for the input, build and save contract. This reference adds the physics method and the pitfalls observed when an arcade movement model was replaced.

## Procedure

1. **Gather the measured baseline first.** Write one frozen table of SI values with a source comment for each: gravity, stature, reach (about 1.33 × stature), walk, run and sprint speeds, sprint force-velocity intercepts, sole friction μ, comfortable braking, drag, takeoff velocities and push-off. Derive everything else from it. Tuning later changes the table, not scattered constants.
2. **Measure reference footage when the user supplies it.** Confirm which clips are real time. Slow-motion clips are common and give much smaller takeoff speeds. Count flight frames at the native rate and use v = g·t/2. Record the frame numbers and the clip time with the evidence, and keep the footage outside the skill.
3. **Keep the model pure and thin.** Expose renderer-free functions for drive acceleration, the ground step, facing, push-off, landing retention and ballistic reach. The game loop calls them and the tests import the same functions. The [locomotion example](../assets/locomotion-example/README.md) is a runnable starting point.
4. **Make transitions continuous.** Low-pass the acceleration over the time legs take to build force (about 80 ms). Bound the total horizontal force by a friction circle. Slow into cuts with cos(turn), and rate-limit facing with a pivot speed. Do not add a hard speed cap in place of these: in the originating run, a cap produced jerk spikes.
5. **Write each bound as a formula.** Examples are stopping distance = v²/2a + v·τ, lateral acceleration ≤ μg, a facing step of at most pivot·dt, and a 30 m sprint time from the force-velocity curve. When the realistic model changes an old test, replace the threshold with the derived value and comment it. Do not loosen it until it passes.
6. **Prove each new check is sensitive.** Run it against a copy with the fix removed or the smoothing disabled, and require a failure. Record both results.
7. **Re-check level feasibility headlessly.** Realistic speeds and jumps can make an existing course impassable. Simulate each required traversal with the game's own step, collision and ledge functions on the real terrain: hops, pull-ups, wall-runs and roof access. Also assert that areas meant to be out of reach stay out of reach. Respace the level, not the physics, unless the user approves an ability.
8. **Declare non-physical abilities.** Abilities kept for play, such as glide, thermals or a separate combat mode, should be listed in the UAT known limits so testers do not report them as regressions.
9. **Drive the real build in the browser.** Run the journey with synthetic input, keep per-frame traces such as heading and speed, and write them before the assertions so a failure keeps its evidence.

## Pitfalls observed

| Symptom | Cause | Response |
| --- | --- | --- |
| Runner orbited its target | Constant speed through a sharp turn exceeded the friction radius | Cut speed = max · max(floor, cos δ), braking at μg |
| Scripted autopilot overshot jumps and ledges | Realistic braking takes metres | Braking-aware autopilot plus a bounded retry, with a pilot trace on failure |
| Wall-jump re-caught the same wall | Wall detection on the next frame | Latch the wall just left; clear the latch on ground contact |
| Eave just out of reach | Reach and wall-run lift set by guess | Anthropometric reach; set wall-run vertical speed to max(current, lift) |
| Angled jump attacks swung half-turned | Pivot smoothing applied to combat aim | Exempt attack and aim intent from facing smoothing |
| Leftover acceleration after a teleport or stop | Filter state not cleared | Zero the filtered acceleration wherever velocity is zeroed |
| Synthetic key taps sometimes missed | Tap shorter than a rendered frame | Hold taps for at least one rendered frame; wait on the frame counter |
| Browser suites timed out at about 0.2 fps | Software GL under memory pressure. The unchanged baseline failed the same way | Check free memory, run the same commit as a baseline, use verified hardware GL (`BROWSER_GPU=1`), and record the renderer |
| Screenshots stalled an otherwise passing run | Capture timeout on a slow renderer | Longer timeout; a failed capture is logged, not fatal |

## UAT handoff

Stop the previous UAT server before relaunching. Rebuild an isolated copy and serve it on a port separate from the player's preview. The port is a separate save origin, so an empty save there is expected. Confirm the listening process's working directory and that the served bundle contains new identifiers. Give one table of feel steps with expected physical numbers, such as a 0.37 m standing rise or about 0.3 s to reverse facing. Ask the tester to report the first failing step and whether it felt too slow, too stiff or too floaty. Name the one or two parameters that map to each answer.

## Capture decision and provenance

Factors follow the skill-capture rubric in this order: outcome, inputs, procedure, resources, validation.

| Candidate | Factors | Score | Decision |
| --- | --- | ---: | --- |
| full-stack-app-creation | .75, .75, .75, .75, .75 | 75% | Extend, as directed by the user. The playable-3D mode already covers fixed steps, frame-aware input, the build, saves and UAT, and the suspension example sets the pure-solver pattern. New material: a measured baseline, transition smoothing, formula-derived bounds and headless course feasibility. |
| 3d-modeling | .25, .25, .25, .25, .25 | 25% | Receives only the soft-attachment collider; see [runtime character fit](../../3d-modeling/references/runtime-character-fit.md#soft-attachments-in-motion). |
| smoke-test | .25, .5, .25, .25, .75 | 36.25% | Its incremental, retained evidence log was used as the progress check. No physics method was added there. |

| Resource | Disposition |
| --- | --- |
| Locomotion module and its physics tests | Generalized into the [locomotion example](../assets/locomotion-example/README.md) with a sensitivity test. Character name, game constants unrelated to locomotion, and project paths were removed. |
| Parkour, course layout, terrain and browser suites | Retained with the originating project, because they depend on its world. The method is in steps 7 and 9. |
| Reference footage and frame strips | Not bundled (third-party media). The measurement recipe is in step 2. |
| Gate logs, UAT form, smoke log | Kept in task evidence outside the skill. |

Historical feedback, paraphrased:

- The user asked for real life as the baseline for collision, climbing, speed and velocity, in thin code, with incremental smoke evidence. The response was one measured table, pure functions and a 25-row evidence log. The full gate passed on hardware GL. Physical controller feel stayed a human UAT item.
- The user asked for smoother turning transitions and refined tests. The response added force rise, the friction circle and pivot-limited facing. Measured jerk fell from about 350–710 to 100–130 m/s³. Reversal facing steps fell from π to 0.167 rad per frame. The new smoothness and reversal checks fail with smoothing removed. Feel was handed to UAT rather than claimed.

Generalized values include the project, branch and character names, ports, local paths, evidence locations and renderer identity.
