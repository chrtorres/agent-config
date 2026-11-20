# Footage Editor

A local browser editor for a person recorded in a portrait video. It generates the pose, foreground, editable anatomy, skin masks, cleanup tracks, and recorded-motion preview from the supplied MP4 each session. The editor includes live pose controls, frame-by-frame inspection, independent main video zoom, named and custom areas, and a native or 4K canvas.

## Start

Use Linux with a writable tmpfs at `/dev/shm`, Python 3.10–3.12 (verified on 3.10), and an H.264 and WebGL capable browser. Allow room in tmpfs for the generated 4K video, tracking, and browser validation. Prepare an isolated Python environment.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B run.py
```

Enter a path at the hidden prompt. The application also accepts a single path line on standard input. Open the loopback URL when preparation and verification finish. Press Ctrl+C in the launch terminal to end the session.

The supported input is a single-shot, even-sized 9:16 portrait MP4 with one H.264 stream, one AAC stream, constant presentation cadence starting at zero, and a sufficiently visible performer. MediaPipe supplies generic pose, face, hand, and skin inference. The launcher downloads four checksum-verified public model bundles. For offline use, supply the same model files through `--models <model-directory>`. Their names, upstream locations, and hashes are declared in `run.py`.

## Edit

Use **Video zoom** or Ctrl/⌘+scroll, then drag to pan. Click a visible named detail, or choose **Pick custom area** and click a foreground point. Width and Height support −70% to +110% in half-percentage-point steps. Use **Clean image** to ease interacting edits. The displayed video and its sound follow the recording's timing. Large deformations can stretch local texture, and details can be unavailable when occluded.

The source endpoint reads the original MP4. The engine verifies native bytes and checks picture timestamps, duration, and audio against the 4K upscale. The upscale preserves timing and composition. Use **Download edit settings** to export a recipe when you want to retain one explicitly.

## Privacy and lifecycle

The package contains engine source and synthetic tests. Media and person-derived data are processed locally. Session outputs, models, masks, landmarks, and motion data go to a user-private tmpfs directory that is removed on orderly exit, including Ctrl+C and SIGTERM. Pass the path through standard input so it stays out of command arguments. HTTP binds to loopback with no request logging and no-store responses. The only engine network fetches are for the fixed public model artifacts.

Use a local browser profile that meets your privacy requirements. Explicit downloads are managed by the browser. System settings for swap, crash collection, browser behavior, and forced termination govern host-level retention. The engine disables its own core dumps.

## Validate

`run.py --check` runs all processing and validates the media before releasing the session. To test the UI, run the editor and pass the reported loopback URL, installed Playwright package directory, and browser executable to the session checks.

```sh
.venv/bin/python -B -m unittest discover -s tests
node tests/transport.mjs
node tests/secondary-kernel.mjs
node tests/session.mjs <loopback-url> <playwright-package-dir> <browser-executable>
node tests/stage-zoom.mjs <loopback-url> <playwright-package-dir> <browser-executable>
```

For parity testing when an approved comparison viewer is available, pass its URL as a fourth argument to `session.mjs`. It compares large images in browser memory and reports pass/fail. Keep real-source validation transient and retain aggregate results only.
