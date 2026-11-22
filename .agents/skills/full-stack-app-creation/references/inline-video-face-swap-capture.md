# Inline video Face Swap capture

## Comparison and decision

Factors are in the order outcome, inputs, procedure, resources, and validation. Scores use the [skill-add weighted rubric](../../skill-add/references/skill-comparison.md) and describe coverage before this update.

| Candidate | Factors | Score | Prior coverage |
| --- | --- | --- | --- |
| [3d-modeling](../../3d-modeling/references/footage-motion.md) | .75, .75, .50, .50, .75 | 62.50% | Covered localized motion, occlusion and protected pixels. The prior procedure lacked eye masks and motion-gated seam blending. |
| [full-stack-app-creation](source-only-footage-editor.md) | .75, 1, .50, .50, .75 | 66.25% | Covered the local editor, volatile media, frame verification and a separate still-photo workflow. The bundled editor lacked the inline swap, destination lock, and integrated export checks. |
| [product-refinement](../../product-refinement/SKILL.md) | .25, .25, .25, 0, .50 | 23.75% | Covered targeted revision and measured regressions with no footage-specific procedure or fixture. |
| [smoke-test](../../smoke-test/SKILL.md) | .25, .25, .25, .25, .50 | 27.50% | Covered isolated smoke runs and evidence retention. The editor-specific inference, frame exactness, and browser journey belong in the example. |

The user explicitly requested extensions to both named skills. The app skill owns the runnable editor and the modeling skill owns the motion procedure, with cross-links between them. The still-photo workflow remains available for a still-to-still task.

## Feedback and observations

| Historical user feedback, paraphrased | Implementation response and observed check |
| --- | --- |
| Keep Face Swap inside the editor, with video stills, drag and drop, and editing while it processes. | The browser exercised the inline tool, both drop zones, a donor-frame pick, existing Quick Review controls while processing, verified preview, and clear. |
| The wrong face was picked. Allow selection and zoom. | The picker requires explicit selection and confirms with a registered green mask. The browser tested keyboard selection at 3× zoom and zoom reset. Multi-person association still depends on detections and confidence. |
| Inspect several green layers based on facial curvature. | Relative-depth slices split the semantic mask. Synthetic tests verify disjoint coverage and ordering. The slices represent visible image-derived depth. |
| Clean up eye tracking and fast twitches. | Current-frame eye protection and motion-gated seam blending have direct array tests. In the historical 34-frame reference excerpt, 33 frames used eye protection, 30 used seam stabilization, and one reset history on fast movement. All frames and outside-mask pixels passed the reported verification. This was a short engineering check of one excerpt. |

The later upload regression reproduced a working landing page followed by HTTP 500 when the launch interpreter lacked PyAV. The launcher now checks the core media runtime before listening and uses the project environment when available. The bundled upload smoke drives the user-facing path from Python with site packages disabled. Setup failure without a usable environment has a separate regression test.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Local app, controller, inference, RGB compositor, model fetchers, media verification, and tests | Captured together in the [standalone editor](../assets/footage-editor/). The Python requirements are pinned. |
| Test media | [Fictional portraits](../assets/photo-face-swap/make_fixture.py) are drawn with Pillow. The [clip generator](../assets/footage-editor/tests/make_face_swap_clips.py) creates H.264 inputs and AAC for the target, including three deliberately blank frames. |
| Runtime and public inference objects | Python, Node, Playwright, and Chrome are external prerequisites. FFmpeg comes through the pinned Python dependency. The checksum-gated fetchers document acquisition of the external OpenCV Zoo, FaceFusion and MediaPipe model artifacts. Upstream rights apply. Installed dependencies and weight caches are excluded. |
| Private recordings, portraits, derived renders, session data, and machine identity | Excluded. Only aggregate observations from private verification are retained here. Commands use discovered runtimes and caller-supplied directories and URLs. |
| Fresh logs, commands, synthetic screenshots, and source hashes | Retained outside the shared skills in the isolated validation workspace. |
