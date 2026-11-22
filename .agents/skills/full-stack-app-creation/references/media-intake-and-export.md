# Media intake and edited downloads

Use the [standalone Footage Editor](../assets/footage-editor/README.md) for a runnable local example. The [modeling clock checks](../../3d-modeling/references/footage-motion.md#footage-clock-and-rendition-checks) define how to keep the displayed image and tracked layers registered.

1. Inspect the file header and decode a frame before starting preparation. Preserve the original for an exact download. When needed, make an upright, browser-compatible H.264 working copy with optional AAC and verify decoded frame count and relative presentation times. Use Quick Review to expose a conversion action when the browser cannot decode the selected video directly.
2. Carry source frame offsets through tracking, playback, seeking, and export for variable-cadence input. Show the current preparation stage. Keep 4K generation out of the native preparation path. Serve the 4K artifact after it passes verification and offer a retry if generation fails.
3. Offer downloads at the point of editing. In the example, Quick Review exports stills as PNG and adjusted video as MP4. The motion editor snapshots shape and tone settings into a lossless RGB MP4 at native resolution and exports the rendered live pose as a PNG. The [Face Swap flow](inline-video-face-swap.md) has its own verified video download.
4. Exercise invalid input and the normal launch-to-edit path. Run a format matrix with silent and variable-cadence inputs. Inject a single 4K encoder failure, verify native playback, retry 4K, then decode the files obtained through the real download controls. Check changed pixels, image size, frame counts, presentation timing and the prepared AAC track where applicable.

## Reproduce the browser matrix

Install the [editor prerequisites](../assets/footage-editor/README.md). Use any authorized short clip with a consistently visible performer and enough resolution for tracking. The fixture generator creates MP4, silent MP4, HEVC MOV, VP9 WebM, MKV, AVI, and three drawn still-image variants. The original recording is an external fixture input. Use a writable tmpfs for private fixture generation and let the smoke harness manage its temporary working files. Keep de-identified results.

From a fresh copy of the editor, use the pinned Python environment, an installed Playwright package directory, and a compatible Chrome executable.

```sh
python -B tests/make_media_fixtures.py <short-performer-clip> <new-fixture-directory>
python -B tests/smoke_media.py --fixtures <fixture-directory> \
  --playwright <playwright-package-dir> --browser <chrome-executable>
```

The launcher can download the public MediaPipe models or receive a checksum-verified model directory through `--models`. The compatibility and Quick Review encodes can convert chroma and transcode non-AAC audio. The test matrix verifies relative picture times within 1 ms after these conversions and exact MP4 frame timing and AAC for the tested lossless shape-and-color export. [Capture decisions and resource inventory](media-intake-and-export-capture.md)
