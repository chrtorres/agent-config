# Code video capture decision

The user asked to preserve the workflow with source details removed and add code-driven video to both existing skills. The capture uses a generated 2D animation, a procedural Blender scene and a synthesized tone. It preserves the earlier method of timed sample reassembly and content verification through a generic remux example. A specialized container reconstruction remains an option when whole-file identity is required.

## Pre-extension comparison

Factors use the skill-add weights in order of outcome, scope, procedure, resources and validation. Percentages describe the incoming combined video authoring and preservation method.

| Candidate | Factors | Score | Evidence and decision |
| --- | --- | ---: | --- |
| 3d-modeling | .50, .50, .50, .50, .50 | 50% | Animated figure review covers pose timing, Blender scene generation and spatial inspection. MP4 encoding, audio and packet comparison were missing. Extend per user direction and keep the shared implementation here. |
| full-stack-app-creation | .25, .25, .50, .25, .50 | 36.25% | Animated playback and browser QA cover integration and observed state changes. The existing example delivers GLB rather than encoded video. Extend per user direction and reference the canonical video example. |
| smoke-test | .25, .25, .50, .25, .50 | 36.25% | Synthetic stimuli, HTTP and browser capture support the testing method. The existing harness exercises GLB rather than MP4. Apply the method to the video capture. |
| live-app-recreation | .25, .25, .25, .25, .50 | 27.5% | Live behavioral recreation and browser QA share visual acceptance techniques. The deliverable is an operable interface. Leave this candidate outside the extension. |

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Frame generation, encoder, remux and comparison | Bundled as `video.py` and `blender_frames.py` with synthetic parameters and caller-supplied paths. |
| HTTP and browser verification | Bundled as `smoke.py` with isolated loopback serving and a dynamically assigned port. |
| Original media, packet data, actors, models, overlays, locations, labels, audio, screenshots and reference identifiers | Excluded from the capture. Runtime paths, addresses, filenames and original-media hashes are omitted. |
| Short clips, frame PNGs, logs and browser screenshot | Regenerated in isolated run evidence. |
| Python libraries, browser and Blender binaries | Declared external prerequisites. The dependency list records the tested Python package versions. |

The source-data removal request was verified by running the bundled material in a standalone synthetic sandbox. The delivered example covers content-preserving remux on its declared input format. File equality is a separate measurement.
