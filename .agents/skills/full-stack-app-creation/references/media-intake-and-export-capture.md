# Media intake and edited download capture

## Routing

The user explicitly requested both existing skills. Coverage factors are ordered by outcome, inputs, procedure, resources, and validation. Scores measure the state before this update using the [weighted comparison rubric](../../skill-add/references/skill-comparison.md).

| Existing skill | Coverage factors | Overlap | Prior coverage and destination |
| --- | --- | --- | --- |
| [3d-modeling](../../3d-modeling/references/footage-motion.md) | .50, .50, .50, .50, .75 | 52.50% | Covered native clock, mapped geometry, and 4K fidelity. Extend the footage procedure with frame intervals and each rendition's verification. |
| [full-stack-app-creation](source-only-footage-editor.md) | .75, .75, .50, .75, .75 | 66.25% | Covered upload and an editable local session, media checks and an earlier engine. Extend the bundled editor and add its format, recovery, and export workflow. |
| [smoke-test](../../smoke-test/SKILL.md) | .50, .25, .25, .25, .75 | 36.25% | Covered isolated browser checks and evidence. The codec fixtures, fault injection, and export contract fit the two requested extensions. |

The two references share the app example and regression harness. Modeling review and print approval remain governed by their existing procedures.

## Feedback and evidence

| User feedback, paraphrased | Captured response and historical observation |
| --- | --- |
| Preparation failed at the playback verification step. | Native preparation finishes independently of 4K. The regression deliberately failed the first 4K encode, checked native availability, and retried successfully. The original encoder failure detail was unavailable. |
| Exercise different file types and fix conversion problems. | The matrix includes six video inputs and three still formats. AVI exposed uneven frame intervals. The app now carries decoded frame offsets, and the test verifies each output against its own input. |
| Offer a download during editing. | Quick Review provides PNG or MP4, and the prepared editor provides lossless shape and color MP4 and live frame PNG. Browser downloads are decoded and compared for size, changed pixels, timing, and prepared audio. |
| Catch failures earlier through smoke tests. | The reusable browser matrix spans input through download, with both a forced 4K failure and recovery. A separate launch-to-upload smoke covers a Python environment missing site packages. |

## Resources

| Resource | Disposition |
| --- | --- |
| Frontend, HTTP routes, conversion, frame clock, variant verification, and editor export | Captured as source in the [editor bundle](../assets/footage-editor/). |
| Format fixture builder, browser journey, failure injection, and pixel/timing assertions | Bundled under [tests](../assets/footage-editor/tests/). The frame timing unit test generates synthetic silent WebM. The full tracking matrix uses an external authorized performer clip. |
| Codecs and model files | The pinned Python requirements include PyAV, Pillow and FFmpeg via imageio-ffmpeg. Chrome and Playwright are external test dependencies. Public model URLs and checksums are in the launcher and Face Swap fetcher. |
| Private footage and generated media | Excluded. The generator makes variants in task-local storage and the harness cleans up copied fixtures and downloads. |
| Run evidence | Historical outcomes above are sanitized summaries. Fresh logs and source hashes belong outside the skills. Generalized values include source and fixture paths, model directories, browser and Playwright paths, loopback ports, and session identifiers. |
