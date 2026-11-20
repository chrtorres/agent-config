# Interactive motion on recorded footage

- Clarify whether the controller selects filmed frames, retargets a 3D rig, or drives a newly inferred pose over source footage. For direct control, keep simulation time and media time independent. Support travel, jump, selection of independent body parts, persistent per-part poses, reset, and a separate time transport when they are in scope.
- Make the decoded frame the render input. Index shot metadata by the displayed media frame, read its native dimensions, and carry control state across cuts. Update masks and scene data together. At neutral render the original texture directly. During motion draw a clean plate only where the actor is removed, composite the moved textured mesh, and protect picture-in-picture graphics or other designated foreground occluders. Route the same movement through the reflection with the appropriate camera transform.
- Poll the standard Gamepad API from the render loop. Handle activation, dead zones, disconnect, tab suspension, edge-triggered jump and reset, and switching between devices. Use a fixed simulation step with elapsed-time clamping. Retain keyboard and pointer equivalents. Discover the browser, playable codecs, port and device at runtime.
- Use loopback byte-range serving for the exact MP4. Test reported dimensions and time during paused seeks and forward playback across cuts. Compare rendered neutral pixels after reset, verify protected pixels after composite, and measure travel and an independent joint change in the same sampled frame. Include reflected motion, combined controls, responsive layout, and a targeted negative case when fixing a regression.
- Distinguish injected browser input, OS-level virtual controller tests, and a person operating the physical controller. In UAT cover independent travel and articulation during playback and pause, simultaneous controls, jump and landing, retained pose after camera cuts, and reconnection. Report reconstruction artifacts in areas the camera could not see. [Model and media preparation](../../3d-modeling/references/footage-motion.md)

## Run the portable fixture

Copy the two referenced asset directories to sibling directories in a fresh retained workspace. Put the modeling fixture in a directory named `model` and the browser fixture in `app`. Install the modeling fixture's documented Python dependencies in an isolated environment. Install Playwright with a compatible Chromium or supply an installed compatible browser that decodes H.264. Pass the absolute Playwright package directory and optional browser executable to the check.

~~~sh
python3 -B model/generate.py data
python3 -B app/serve.py data
node app/check.mjs <printed-loopback-url> evidence <playwright-package-dir> <browser-executable>
~~~

The server prints an allocated loopback URL. The smoke check uses synthetic standard-layout input and observes travel, pose, jump, changing widths, reflected rendering and exact reset. Retain screenshots and execution logs in the test workspace. [Browser example source](../assets/footage-motion/) · [Modeling fixture](../../3d-modeling/assets/footage-motion/) · [Capture inventory](../../3d-modeling/references/footage-motion-capture.md)

## Verify a generalized build against the original

When an original download and an edited review are both required, give the launcher explicit paths to each. The selected review video must match its timeline. The source endpoint reads the supplied MP4 directly and supports byte ranges. Download both complete responses and compare each with its corresponding reference file using `cmp` or SHA-256.

~~~sh
python3 -B app/serve.py <timeline-parent-directory> --video <review-mp4> --source <original-mp4>
curl --fail <printed-loopback-url>source.mp4 --output <returned-source-mp4>
cmp <original-mp4> <returned-source-mp4>
~~~

Prepare the original and the generalized review in a private workspace. Feed both the same task-local video, fitted landmarks, and artwork layers. Match the browser and graphics backend. Disable live controller polling in both pages and replay the same deterministic inputs. At the beginning, end, and either side of each cut, wait for the decoded frame and render to settle. Compare the entire canvas and evaluated joint positions with a neutral pose and an active pose. Repeat the reference acceptance suite on the generalized build. Run the synthetic fixture independently and check its regenerated media for determinism. Record the specific frame and input coverage when reporting equality.

Read caller-supplied media from its existing location. Create any derived media, tracking, renders, frame captures, hashes, and detailed comparisons in a temporary workspace. Retain only results that omit source identifiers and subject data. Stop the source review server and remove the temporary source-derived files when verification ends. Use synthetic inputs for retained tests, instructions, and examples. Reproduction of a particular recording requires its inputs again.

## Manifest contract

The fixture uses an integer frame index with zero-based, half-open shot intervals. Each frame record contains the native width, ordered performer and optional reflection layers, and a foreground coverage diagnostic. Each layer stores projected x and y in quarter-pixel units and confidence as a percentage in the landmark order declared by the manifest. Height, frame rate, atlas tile size, downsample factor, and atlas grid size are shared. Each page pairs an RGB matte atlas with a clean-plate atlas. The red matte channel belongs to the performer and green to the reflection.

Each shot supplies a protected rectangle in canvas coordinates and reflection clipping bounds. An optional fifth reflection value is the bottom boundary slope per horizontal pixel. An optional per-shot vertical travel range bounds root movement. Author these values from the task footage and keep the resulting manifests and atlas images in task-local storage. The demo generator supplies synthetic values. Compile shader atlas dimensions from validated manifest values so rounding matches equivalent fixed-dimension builds during exact-pixel comparisons.
