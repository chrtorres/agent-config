# Recover a failed swap and review it in the main viewer

**Diagnose the worker.** Read the POST response body and the worker's terminal error. A copied browser request may omit its binary body. The status endpoint reports the current job phase, and several different processing errors return HTTP 422. Reproduce with a fictional portrait and clip before changing face selection, upload validation or verification.

**Retry a GPU allocation failure once.** If the inference runtime reports memory exhaustion on the GPU, replace the worker process with a CPU-only invocation using the same inputs and output directory. Process replacement releases all accelerator sessions and preserves the server's cancellation target. Gate the retry on the active provider and the specific error. Publish the result after the ordinary decoded-frame, audio and outside-mask checks pass. Run a failure-injection check with actual CPU inference.

**Compare the actual result.** Let both the viewer and the side panel switch between the swap and the original. Use a single playback element and mirror its presented frames to a small sidebar canvas so the two views share time and audio. Seek to the original playhead when showing the swap. Restore that time when switching back. Handle still images on load, pause hidden playback, and stop the mirror callback on exit. Bind the result to its target. Publish prepared-target provenance with the job so reloading the prepared editor can restore comparison. Quick Review uses the selected local file within the page lifetime.

**Export learned styles.** Snapshot the validated library under its lock. Archive each complete JSON record under its stable library filename. On the user's click, open the save picker before asynchronous network work, then stream the response into the chosen file. Handle cancellation separately and use a browser download when the picker is unavailable. Check each extracted filename and JSON record against the source library. The native destination dialog requires a human selection.

## Replay with fictional media

Use the bundled editor, its requirements, verified weights, and the portrait and clip generation commands in [the inline swap workflow](inline-video-face-swap.md#reproduce-with-fictional-footage). Run the following from the copied editor with its Python environment active.

```sh
python -B tests/check_cpu_retry.py <generated-fixtures> <face-model-directory> <mesh-model-file>
python -B run.py --models <offline-model-directory> --face-models <face-model-directory> --styles <scratch-library>
```

Run `tests/face-swap.mjs` as documented in the inline workflow against the printed URL. It drives a real swap from Quick Review, plays and seeks the verified result, checks the sidebar and restores the original playhead. Run `tests/check_comparison_modes.mjs` with the same arguments against an idle fixture server. It renders a real still swap, then reloads the prepared shell with a simulated ready report to exercise its two buttons.

To exercise export independently, launch the following fixture. It serves the prepared editor shell with one real profile measured from fictional footage. It bypasses pose preparation and CNN measurement.

```sh
python -B tests/style_export_fixture.py <generated-fixtures>/target.mp4 <new-work-directory>
```

In another terminal run the browser check with that fixture's URL. Compare the contents of both archives with every JSON file in the fixture library. The browser check uses a real origin-private file handle for the picker branch and exercises a download and cancellation. Stop each fixture server when finished.

```sh
node tests/check_style_export.mjs <fixture-url> <playwright-package-directory> <chrome-executable> <work-directory>
python -B -m unittest discover -s tests -p test_recording_style.py
```

## Capture decision and resource inventory

The user requested updates to both existing skills. The factors below assess coverage before capture, in order of outcome, inputs, procedure, reproduction resources and acceptance. Weights are 25, 15, 35, 15 and 10.

| Candidate | Factors | Score | Evidence and decision |
|---|---|---:|---|
| full-stack-app-creation | 1, .75, .75, .75, .75 | 81.25% | The same runnable editor, binary swap request, status routes and browser checks already covered the primary journey. Style library records, provider retry and simultaneous review were missing. Extend the existing application bundle. |
| 3d-modeling | .5, .75, .5, .75, .5 | 57.5% | The face-compositing reference already covered the footage inputs, masks, original-pixel checks and fictional fixtures through the shared editor. Its remit covers visual verification. At the user's request, extend its comparison guidance and link to the runnable sibling. |

| Historical user feedback (paraphrased) | Implementation and observed check | Limit |
|---|---|---|
| A prepared swap failed with 422. | A fictional run reproduced GPU allocation failure. A forced GPU failure followed by real CPU inference produced a verified result. | The original POST response and media were unavailable for diagnosis. |
| Show the swap in the main viewer as well as the sidebar, with a way back to the original. | Main-stage and sidebar controls share a player and restore the playhead. Browser checks covered moving footage, a still and a restored prepared-result state. | The historical prepared-reload test supplied the ready state as a fixture. |
| Save learned styles in a chosen folder. | The save and download paths produced archives whose extracted records matched the stored library. | Browser automation substituted a file handle for the native dialog. |
| Stop the local editor when requested. | Identify the listener, terminate its owning editor and verify exit and port closure. | Discover the active endpoint and process at use time. |

The [editor bundle](../assets/footage-editor/) contains the affected UI, HTTP routes, worker, style measurement and library code, fixture generators and tests. The sibling [portrait generator](../assets/photo-face-swap/make_fixture.py) regenerates fictional source images. The clip generator supplies the target video and expected missing-face frames. Runtime dependencies, a browser with H.264 support, Playwright and checksum-verified public inference models are external prerequisites. The editor README and fetcher identify their setup and provenance. Regenerate exports, previews and archives locally. Private recordings, portraits, learned profiles, installed packages, weights and machine-specific logs are excluded.
