# Inline video Face Swap

Use the [bundled editor](../assets/footage-editor/) as a working slice for an authorized local video face edit. The [motion-aware compositing procedure](../../3d-modeling/references/face-motion-compositing.md) covers alignment, eye preservation, relative-depth mask inspection, and motion gating.

1. Put Face Swap next to the existing editor tools. Accept a source still or a selected frame from a source video. Keep video frame selection in the browser and send only the selected source still. Require an explicit destination pick on the actual displayed frame. Provide keyboard access, independent target zoom, and an overlay that uses the same viewport transform as the target.
2. Run inference, encoding, and verification in a background job. Preserve the user's active editor session while the job runs. Expose observable progress, cancel, clear, and actionable errors. Publish the result only after verification.
3. Keep source media, derived imagery, and person-specific data in the volatile local session. Verify public weights by checksum. Keep file delivery on the loopback interface with no-store responses and restrict mutating routes to same-origin requests. Explicit exports leave the session through the browser's normal download flow.
4. Keep preview playback and the verified export separate where the target browser benefits from a simpler playback rendition. The bundled export uses lossless RGB H.264 and copies AAC when present. Check frame count, timestamps, durations, decoded composite hashes, outside-mask pixel equality, and AAC payloads and decoded timing. Test decoded preview colors and normal playback separately.
5. Test modeled motion behavior in deterministic arrays and the actual upload-to-clear path in a browser. Record the verification scope. A passing fixture establishes tested contracts and behavior on that input. For appearance across fast turns, eyelid occlusions, and changing light, compare representative authorized clips at the same playhead.

## Reproduce with fictional footage

Use the runtime and dependency setup in the [editor README](../assets/footage-editor/README.md). For an isolated copy, keep the editor and the [portrait generator](../assets/photo-face-swap/make_fixture.py) together in a scratch workspace. The commands below run from the copied editor. Supply a Python interpreter with the pinned requirements, an installed Playwright package directory, and an H.264-capable Chrome executable.

```sh
python -B -m unittest discover -s tests
python -B ../make_fixture.py ../fixtures
python -B tests/make_face_swap_clips.py ../fixtures
python -B tools/fetch_face_models.py --models <verified-model-directory>
python -B run.py --face-models <verified-model-directory>
```

Open the URL printed by the launcher. In a separate terminal, run the browser test from the same editor directory. To inspect a settled synthetic frame, set `FOOTAGE_SYNTHETIC_SCREENSHOT` to a path in the scratch workspace.

```sh
node tests/face-swap.mjs <printed-loopback-url> <playwright-package-dir> <chrome-executable> ../fixtures
```

The editor fetches the public MediaPipe face model when it needs it. For offline operation, supply a directory containing the verified `face.task` with `--models`; general motion preparation also needs the other listed MediaPipe artifacts. The pinned filenames, upstream URLs, and digests live in [run.py](../assets/footage-editor/run.py) and the [ONNX fetcher](../assets/footage-editor/tools/fetch_face_models.py). Check the upstream terms for each weight before redistribution or deployment.

## Benchmark tracking through action

Build a synthetic action clip with exact ground truth, then compare the earlier per-frame tracker with the action tracker. Run these commands from the copied editor. Use a fictional portrait, such as the one from the portrait generator.

```sh
python -B tests/make_action_face_clip.py <portrait.png> ../fixtures/action.mp4
python -B tests/face_tracking_benchmark.py <portrait.png> ../fixtures/action.mp4 <verified-model-directory> <verified-model-directory>/face.task
```

The benchmark prints placement error, jitter and coverage for both trackers, including a run with detections removed. The method is in [tracking faces through action](../../3d-modeling/references/face-motion-compositing.md#tracking-faces-through-action), and historical numbers are in the [capture record](footage-reshape-tracking-capture.md). The browser test `tests/face-swap.mjs` predates the tabbed editor and needs its panel selector updated before use.

See the [capture record](inline-video-face-swap-capture.md) for implementation scope, resource disposition, and historical results.
