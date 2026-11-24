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

**Hair and feature color** dyes hair, lips, eyes (irises only, inside the eyelids), and eyebrows. Pick a color and a strength for each. A dye takes the chosen hue and saturation and keeps the pixel's shading, lifting its lightness partly toward the chosen color (more for hair, so dark hair can go lighter). Hair comes from the per-frame segmentation masks, steadied over time: each frame's hair weight is averaged with four frames on each side, warped onto it with optical flow and weighted by how well they match, so the dye no longer flickers or pops in and out. At full resolution the hair weight follows the frame's own edges (a joint bilateral upsample guided by lightness stored with the masks), so the dye stays in the hair instead of spilling a soft halo onto the background. Videos prepared before this change need preparing again for both. Lips, irises, and brows come from tracked face-mesh outlines, so the color follows the face. The export applies the same colors.

**Download original** returns the uploaded file byte for byte, in its original container. **Download shape and color edits** renders the current shape and skin-tone settings to lossless RGB MP4 at native resolution, with verified video timing and the prepared AAC track. **Download current frame** saves the visible rendered canvas as a PNG, including live pose. Use the current frame download for live controller poses. Face Swap has its own verified export. **Download edit settings** saves a reusable recipe.

**Watch in 4K** and **Use 4K controls** build a verified 4K copy on demand. The native editor opens independently and stays usable if upscaling fails. Retry from the 4K page. The 4K version preserves framing and fits the video to 3840 pixels on its longest side.

## Performance

Preparation runs pose tracking first, then face tracking, skin masks, and the motion preview in parallel, then cleanup tracks and motion measurement. Skin segmentation and optical-flow measurement process frames on several worker threads and produce byte-identical output to the single-threaded path. 4K encoding and verification use frame-threaded FFmpeg and decode both files concurrently. Face Swap decodes and detects faces on a reader thread and renders several frames concurrently, while tracking, mask blending, and encoding stay in frame order.

Face Swap models run on an NVIDIA GPU through `onnxruntime-gpu`, whose CUDA 12 and cuDNN 9 libraries install as Python wheels and are preloaded automatically. On a machine without a supported NVIDIA GPU, replace that requirement with `onnxruntime==1.22.1`; the same code then runs on the CPU, about five times slower. GPU and CPU results can differ by one or two levels in a small share of face pixels because of floating-point differences, and every export is still verified against its own composite.

## Privacy and lifecycle

The package contains engine source and synthetic tests. Media and person-derived data are processed locally. Browser uploads, session outputs, models, masks, landmarks, and motion data go to a user-private tmpfs directory that is removed on orderly exit, including Ctrl+C and SIGTERM. For scripts, pass the path through standard input so it stays out of command arguments. HTTP binds to loopback with no request logging and no-store responses. The only engine network fetches are for the fixed public model artifacts.

The one exception is the recording-style library (see below). Each learned style is a small JSON file of aggregate numbers, with no frames, faces or sound, saved owner-only under `~/.local/share/footage-editor/styles` (or `$XDG_DATA_HOME`). Choose another place with `run.py --styles <directory>`, and delete styles in the Style tab. Choose **Learned styles → Export saved styles…** to save the whole library as a ZIP in a folder you select. Browsers without a save picker use their download settings. Extract the ZIP into a directory and pass it to `--styles` to use those profiles.

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

## Recording style

The **Style** tab learns how the open video was recorded, then renders the video (now or in a later session, with any video open) in a learned style.

**Learn this video's style** runs `tools/recording_style.py` on the video and measures:

- **Format and encoding:** frame size, frame rate, codec, bits per pixel, keyframe interval, B-frames and colour range.
- **Colour grade:** black and white levels, contrast, the colour cast of near-neutral tones, saturation, and the full lightness and colour distributions used for rendering.
- **Grain and sharpness:** luma and chroma noise, grain size, and edge sharpness.
- **Vignette:** fitted from how the same scenery changes brightness as the camera moves it across the frame, so a dark object near the edge is not taken for vignetting. A camera that never moves leaves it unmeasured.
- **Camera motion:** handheld shake, roll and their frequency, separated from deliberate pans.
- **Sound:** loudness, noise floor, low/mid/high balance, sample rate and channels.
- **Deep look:** channel means and spreads of the first layers of a pretrained CNN (SqueezeNet 1.1 from the ONNX model zoo, run with OpenCV's DNN module). These are the statistics neural style transfer uses to describe style, and they catch overall differences the measures above miss. The 5 MB model is downloaded once per session and checked against a pinned SHA-256; for offline use, put it in the `--models` directory as `style.onnx`.

The new style is compared with every learned style first. When one matches at 95% or more, nothing is added and the tab says the ability already exists, naming the style and the match. Otherwise the style is saved with the name you give it.

**Show the loaded video in this style** is a switch under **Apply a saved style**. Pick a saved style and turn it on: the loaded video is rendered in that style (once per style), then shown in the editor stage from the current playhead. Turn it off to go back to the original editor at the same time. Turning it on again reuses the finished render. **Apply to loaded video** on a library entry selects that style and turns the switch on. The render re-creates each measurement on the loaded video:

1. Crop and scale to the style's frame, and convert the frame rate.
2. Map lightness and colour: a lightness curve, a Monge–Kantorovich colour transfer and a saturation curve, fitted on the cropped frames. The saturation curve's slope is limited so a small coloured detail on a flat background cannot be blown out.
3. Replace the vignette.
4. Sharpen or soften, then reduce or add grain. Both are calibrated on a short sample encoded with the style's settings, so the result measures like the style after compression.
5. Stabilise and add the style's shake, while keeping fast deliberate moves such as whip pans. If the video already shakes in a similar way, its own camera motion is kept and the shake only rescaled.
6. Match loudness and tonal balance, then encode with the style's bitrate, keyframe interval and B-frame setting.

The result is measured like any upload and scored against the style, with a per-group breakdown, and can be downloaded as MP4. It is a new encode, not a lossless edit.

Matching describes recording style, but colour statistics also depend on what was filmed. In the synthetic benchmark (`tests/style_benchmark.py`, clips from `tests/make_style_clips.py`):

- Two parts of the same shoot match at about 97–98%.
- The same made-up camera filming a different scene matches at about 80%.
- Different cameras match at about 30%.
- Re-rendering a clip in another camera's style measures 84–95% like that style. Steadying a handheld clip is the weakest part (camera-motion scores 47–90).
- Re-rendering a video in its own style measures 99% and looks unchanged.

## Face Swap

Install the pinned dependencies, then fetch the public checksummed models:

```sh
.venv/bin/python -B tools/fetch_face_models.py --models ~/.cache/footage-editor/face-models
```

Run it again after updating: Face Swap now also needs the XSeg occlusion model (`xseg_1.onnx`), and stops with a "Missing or unverified model" message until it is fetched.

Open a target MP4 or a still image, then choose **Face Swap** in the editing tabs or expand it in Quick Review. For a video, scrub to a target frame. Use Target zoom and pan for small faces, click the face, and check its green mask. A click on or next to a face selects the nearest one; tilted, turned, small and motion-blurred faces are found by a second search that tries rotated copies, an enlarged window around the click and a lower detection score. An image target produces a verified lossless PNG (**Download lossless PNG**), and **Show swap** shows it in place of the Quick Review picture. Drop or choose a source image or video. For a video, pause or scrub to the frame you want and choose **Use current frame**. Only the selected still is sent from the source video. Start the swap and continue using the other tools while the result renders in the background. Model weights can also be supplied with `run.py --face-models <directory>`.

**Show swap** and **Show original** switch the editor preview at the current playhead. Playback uses a smaller H.264 rendition. **Download lossless MP4** returns the verified RGB H.264 export with its copied AAC audio. Use **Clear result** to release the volatile output files.

After selecting a face, open **Depth bands** to see six independently toggleable green overlays, ordered from near to far. The bands use MediaPipe landmarks to estimate relative depth across the visible face and stay inside the semantic mask. They are an inspection aid for the selected frame, and are based on the camera image rather than measured anatomical depth. [MediaPipe Face Mesh](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh)

Face Swap tracks the face in two passes. The first pass follows the face through every frame: optical flow predicts where it moved, the nearest detection continues the track (so motion blur does not break identity), and the dense face mesh refines the five alignment points on an upright crop, which holds steadier than the detector's points during turns and blur. When the detector misses a frame, flow carries the face for up to half a second, and short slow gaps are bridged. The finished track is smoothed with a forward-and-backward One Euro filter driven by centered speed: still faces are steadied, fast moves are followed without lag, and nothing is guessed across a shot change or through a fast whip. In the render pass the generated face takes the recorded motion blur (the exposure is matched per frame from the face's own sharpness) and, when a 256 px swap is enlarged, regains camera-scale skin texture from the target's skin only. `tests/make_action_face_clip.py` and `tests/face_tracking_benchmark.py` measure tracking against known motion.

During a video swap, frames where the upright detector finds no face get the same rotated, lower-score search, and a face that blurs while moving stays matched when it is where the tracked face just was. Frames with a different person, or where the identity cannot be confirmed, stay original. The swap uses five-point alignment, source identity conditioning, a semantic face mask, and depth- and time-weighted Gaussian landmark observations derived from the editor's optical tracks. Frames with no reliable association remain original. The lossless export preserves the original frame times, verifies each decoded output frame against the composite, and checks exact pixel equality outside the mask.

The compositor preserves iris and eyelid detail from the current target frame. It also keeps the performer's own mouth interior (teeth, tongue and the dark of an open mouth) from the current frame, because the swap generator renders teeth soft and loses the tongue. The generated lips still surround it. The opening comes from the face mesh's inner lip outline, confirmed by the face parser, so closed lips stay fully swapped. A stuck-out tongue is found by colour (redder than the nearby skin, touching the lips and reaching past them) and kept along with the strip of lip it covers. Flow tracking uses only points that move with the skull, so talking and smiling do not pull the head estimate. `tests/make_expression_face_clip.py` and `tests/mouth_expression_benchmark.py` score smiles, open mouths, a stuck-out tongue and talking.

Anything in front of the face, such as fingers, a spoon, a cup or food going into the mouth, keeps its own pixels. The face parser has no hand class, so it labels fingers at the mouth as skin or lips, and the swap used to paint lips onto them and smear the food. An XSeg occlusion model now marks what covers the face in every frame, and the swap mask leaves those pixels untouched. The same mask keeps the motion-blur match measuring the face rather than a fast-moving hand. While a hand hides the mouth corners, the alignment carries them rigidly with the eyes and nose instead of using the face mesh's guess, and flow tracking ignores points on the hand, so the crop does not jump. `tests/make_feeding_face_clip.py` draws a hand bringing food to the mouth with exact occluder masks. The compositor softly matches color along the outer seam, and uses recent depth-weighted samples to steady slow edge changes. It drops the mask history on fast motion and cuts so earlier frames do not pull the edge behind the face. [MediaPipe Face Mesh](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh)

Model references: [FaceFusion swapping](https://github.com/facefusion/facefusion/blob/decc6c9d8f8e014878624452c6e8fe208726b4ec/facefusion/processors/modules/face_swapper/core.py), [4D Gaussian Splatting](https://arxiv.org/abs/2310.08528), and [FFmpeg codecs](https://ffmpeg.org/ffmpeg-codecs.html).
