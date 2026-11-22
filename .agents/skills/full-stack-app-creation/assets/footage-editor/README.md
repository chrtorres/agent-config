# Footage Editor

A local browser editor for a person recorded in a video. It generates the pose, foreground, editable anatomy, skin masks, cleanup tracks, and recorded-motion preview from the supplied video each session. The editor includes live pose controls, frame-by-frame inspection, independent main video zoom, named and custom areas, and a native or 4K canvas.

## Start

Use Linux with a writable tmpfs at `/dev/shm`, Python 3.10–3.12 (verified on 3.10), and an H.264 and WebGL capable browser. Allow room in tmpfs for the generated 4K video, tracking, and browser validation. Prepare an isolated Python environment.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B run.py
```

If you start with a Python that lacks the video dependencies, the launcher uses the project's `.venv` when available. If setup is incomplete, the terminal reports it before opening the editor.

Open the loopback URL printed in the terminal. Drop an MP4 video or an image onto the media picker, or choose a file. Click **Upload and prepare** to open the motion editor. Use **Clear video** to discard the current video and edits and return to the upload screen. Press Ctrl+C to end the service. Scripts can still supply a single path line on standard input.

During preparation, a progress bar shows the upload, then the current step, percent complete, and an estimate of the time left. Use the **×** on the video thumbnail to cancel and clear the selection and Quick Review. If you reload or open another tab, the upload page shows the running job with the same cancel control. Thumbnails are drawn in the selecting tab from its local preview.

4K builds, Face Swap renders, and edit exports show the same kind of progress bar. Pages receive status over one server-sent event stream (`/events`) that pushes a snapshot only when something changes, instead of polling. Background tabs close their stream and reconnect when shown.

Motion tools support MP4 files with one H.264 video stream, optional AAC audio, and a sufficiently visible performer. Other containers and codecs (MOV, WebM, MKV, AVI, HEVC, and so on) are rejected rather than converted. Rotated or non-square-pixel MP4s are made upright in a temporary lossless copy so tracking and playback share one raster. Variable frame timing is carried through the motion timeline. The original remains available byte for byte. MediaPipe supplies generic pose, face, hand, and skin inference. The launcher downloads four checksum-verified public model bundles. For offline use, supply the same model files through `--models <model-directory>`. Their names, upstream locations, and hashes are declared in `run.py`.

## Edit

Choosing a video or image opens **Quick review** in the browser. Zoom, adjust color, or toggle between the original and adjusted preview. Videos also support seeking and playback speed. These controls operate locally before preparation. **Download edited media** exports Quick Review zoom and color as PNG for images or MP4 for MP4 videos. For frame-by-frame performer tools and motion analysis, choose **Upload and prepare**. If the performer cannot be tracked, the media stays open in Quick Review.

Use **Display** to choose **Fit** (whole frame), **Fill** (crop to the viewer), **Stretch** (fill both dimensions), or **Center** (actual size when it fits, otherwise scale down). **Viewer size** changes width and height without changing media resolution. **Full screen** expands the viewer.

Use the **Edit**, **Motion**, and **Shortcuts** tabs to switch tools while keeping the recording in view. Choose **Dark**, **Light**, or **System** from the theme selector. The browser stores only the theme preference.

Use **Video zoom** or Ctrl/⌘+scroll, then drag to pan. Click a visible named detail, or choose **Pick custom area** and click a foreground point. Width and Height support −70% to +110% in half-percentage-point steps. Check **Keep proportions** to move Width and Height together. Width and Height resize the whole part at one uniform scale about its tracked center, so its texture keeps its proportions instead of bulging like a lens. The surrounding area makes room over a band that widens with larger edits and never folds. With **Soft-tissue physics** on (the default), the volume an enlargement adds hangs from the tracked part on a damped spring: it lags when the body speeds up and overshoots when it stops. Soft parts (chest, breasts, buttocks, hips, torso) respond most, limbs less, and the head, face, hands, and custom areas stay rigid. The motion is simulated once per shot, so playback, seeking, and the exported video match. Use **Clean image** to ease interacting edits; it also holds observed joint and foot pixels in place. The displayed video and its sound follow the recording's timing. Details can be unavailable when occluded.

**Hair and feature color** dyes hair, lips, eyes (irises only, inside the eyelids), and eyebrows. Pick a color and a strength for each. A dye takes the chosen hue and saturation and keeps the pixel's shading, lifting its lightness partly toward the chosen color (more for hair, so dark hair can go lighter). Hair comes from the per-frame segmentation masks; lips, irises, and brows come from tracked face-mesh outlines, so the color follows the face. The export applies the same colors.

**Download original** returns the uploaded file byte for byte, in its original container. **Download shape and color edits** renders the current shape and skin-tone settings to lossless RGB MP4 at native resolution, with verified video timing and the prepared AAC track. **Download current frame** saves the visible rendered canvas as a PNG, including live pose. Use the current frame download for live controller poses. Face Swap has its own verified export. **Download edit settings** saves a reusable recipe.

**Watch in 4K** and **Use 4K controls** build a verified 4K copy on demand. The native editor opens independently and stays usable if upscaling fails. Retry from the 4K page. The 4K version preserves framing and fits the video to 3840 pixels on its longest side.

## Performance

Preparation runs pose tracking first, then face tracking, skin masks, and the motion preview in parallel, then cleanup tracks and motion measurement. Skin segmentation and optical-flow measurement process frames on several worker threads and produce byte-identical output to the single-threaded path. 4K encoding and verification use frame-threaded FFmpeg and decode both files concurrently. Face Swap decodes and detects faces on a reader thread and renders several frames concurrently, while tracking, mask blending, and encoding stay in frame order.

Face Swap models run on an NVIDIA GPU through `onnxruntime-gpu`, whose CUDA 12 and cuDNN 9 libraries install as Python wheels and are preloaded automatically. On a machine without a supported NVIDIA GPU, replace that requirement with `onnxruntime==1.22.1`; the same code then runs on the CPU, about five times slower. GPU and CPU results can differ by one or two levels in a small share of face pixels because of floating-point differences, and every export is still verified against its own composite.

## Privacy and lifecycle

The package contains engine source and synthetic tests. Media and person-derived data are processed locally. Browser uploads, session outputs, models, masks, landmarks, and motion data go to a user-private tmpfs directory that is removed on orderly exit, including Ctrl+C and SIGTERM. For scripts, pass the path through standard input so it stays out of command arguments. HTTP binds to loopback with no request logging and no-store responses. The only engine network fetches are for the fixed public model artifacts.

Use a local browser profile that meets your privacy requirements. Explicit downloads are managed by the browser. System settings for swap, crash collection, browser behavior, and forced termination govern host-level retention. The engine disables its own core dumps.

## Validate

`run.py --check` accepts a video path and runs all processing and media validation before releasing the session. To test the UI, prepare a video and pass the reported loopback URL, installed Playwright package directory, and browser executable to the session checks.

```sh
.venv/bin/python -B -m unittest discover -s tests
node tests/transport.mjs
node tests/secondary-kernel.mjs
node tests/session.mjs <loopback-url> <playwright-package-dir> <browser-executable>
node tests/stage-zoom.mjs <loopback-url> <playwright-package-dir> <browser-executable>
```

Run the upload smoke check with an installed Playwright package, a Chrome executable, and a short supported MP4 with a visible performer. Prefer a fictional fixture. For authorized private input, use a temporary local path and retain only the check outcomes.

```sh
.venv/bin/python -B tests/smoke_upload.py --fixture <valid-mp4> \
  --playwright <playwright-package-dir> --browser <chrome-executable>
```

The runner simulates a launch with the video dependencies hidden, then uses the real browser to test invalid input, valid upload, playback, both canvas sizes, clear, and upload again. To test an editor you already started, run `node tests/upload.mjs <loopback-url> <playwright-package-dir> <browser-executable> <valid-mp4> [display-widthxheight]`.

For a broader browser check, generate short MP4, silent MP4, rotated MP4, PNG, JPEG, and WebP inputs, plus MOV and WebM files that must be rejected, and run the media workflow against a fresh editor session. This check exercises preparation, playback, the original downloads, Quick Review edits, the lossless shape-and-color export, PNG frame capture, and the MP4-only rejection message. Run fixture generation and browser downloads in temporary memory for authorized private material.

```sh
.venv/bin/python -B tests/make_media_fixtures.py <short-performer-clip> <new-fixture-directory>
.venv/bin/python -B tests/smoke_media.py --fixtures <fixture-directory> \
  --playwright <playwright-package-dir> --browser <chrome-executable>
```

The matrix deliberately fails the first 4K encode, checks native playback, and retries 4K successfully before it verifies the downloaded media.

For parity testing when an approved comparison viewer is available, pass its URL as a fourth argument to `session.mjs`. It compares large images in browser memory and reports pass/fail. Keep real-source validation transient and retain aggregate results only.

## Face Swap

Install the pinned dependencies, then fetch the public checksummed models:

```sh
.venv/bin/python -B tools/fetch_face_models.py --models ~/.cache/footage-editor/face-models
```

Open a target MP4 or a still image, then choose **Face Swap** in the editing tabs or expand it in Quick Review. For a video, scrub to a target frame. Use Target zoom and pan for small faces, click the face, and check its green mask. A click on or next to a face selects the nearest one; tilted, turned, small and motion-blurred faces are found by a second search that tries rotated copies, an enlarged window around the click and a lower detection score. An image target produces a verified lossless PNG (**Download lossless PNG**), and **Show swap** shows it in place of the Quick Review picture. Drop or choose a source image or video. For a video, pause or scrub to the frame you want and choose **Use current frame**. Only the selected still is sent from the source video. Start the swap and continue using the other tools while the result renders in the background. Model weights can also be supplied with `run.py --face-models <directory>`.

**Show swap** and **Show original** switch the editor preview at the current playhead. Playback uses a smaller H.264 rendition. **Download lossless MP4** returns the verified RGB H.264 export with its copied AAC audio. Use **Clear result** to release the volatile output files.

After selecting a face, open **Depth bands** to see six independently toggleable green overlays, ordered from near to far. The bands use MediaPipe landmarks to estimate relative depth across the visible face and stay inside the semantic mask. They are an inspection aid for the selected frame, and are based on the camera image rather than measured anatomical depth. [MediaPipe Face Mesh](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh)

Face Swap tracks the face in two passes. The first pass follows the face through every frame: optical flow predicts where it moved, the nearest detection continues the track (so motion blur does not break identity), and the dense face mesh refines the five alignment points on an upright crop, which holds steadier than the detector's points during turns and blur. When the detector misses a frame, flow carries the face for up to half a second, and short slow gaps are bridged. The finished track is smoothed with a forward-and-backward One Euro filter driven by centered speed: still faces are steadied, fast moves are followed without lag, and nothing is guessed across a shot change or through a fast whip. In the render pass the generated face takes the recorded motion blur (the exposure is matched per frame from the face's own sharpness) and, when a 256 px swap is enlarged, regains camera-scale skin texture from the target's skin only. `tests/make_action_face_clip.py` and `tests/face_tracking_benchmark.py` measure tracking against known motion.

During a video swap, frames where the upright detector finds no face get the same rotated, lower-score search, and a face that blurs while moving stays matched when it is where the tracked face just was. Frames with a different person, or where the identity cannot be confirmed, stay original. The swap uses five-point alignment, source identity conditioning, a semantic face mask, and depth- and time-weighted Gaussian landmark observations derived from the editor's optical tracks. Frames with no reliable association remain original. The lossless export preserves the original frame times, verifies each decoded output frame against the composite, and checks exact pixel equality outside the mask.

The compositor preserves iris and eyelid detail from the current target frame, softly matches color along the seam, and uses recent depth-weighted samples to steady slow edge changes. It drops the mask history on fast motion and cuts so earlier frames do not pull the edge behind the face. [MediaPipe Face Mesh](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh)

Model references: [FaceFusion swapping](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/processors/modules/face_swapper/core.py), [4D Gaussian Splatting](https://arxiv.org/abs/2310.08528), and [FFmpeg codecs](https://ffmpeg.org/ffmpeg-codecs.html).
