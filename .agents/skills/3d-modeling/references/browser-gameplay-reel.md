# Deterministic reels from a runtime 3D scene

Use this workflow when a reel should show the actual game renderer, procedural poses or real-time scene. Use the existing [code-generated video workflow](code-video.md) for the media delivery contract and [cinematic presentation](../../full-stack-app-creation/references/cinematic-presentation.md) for render and playability checks.

1. Select shots by the visible motion you need to inspect. Record build identity, initial fixture state, input curve, camera path, framing, fps, and end frame. Stage shots in isolated browser contexts and label staged events. Decide whether to capture the game canvas or the page with HUD.
2. Load the tested production build, wait for needed assets, and settle simulation before capturing. Use an explicit timeline and a test-only frame driver to deliver real app inputs through simulation and rendering. For example, a Playwright init script can advance scheduled animation callbacks at integer tick indices with timestamps derived from fps. Advance input once per tick and capture after the renderer draws. Read WebGL pixels in the same callback batch when the drawing buffer will be discarded. Keep input ramps, pose and cloth continuity, and camera framing reviewable. Retain independent timeouts so a stalled renderer does not produce an incomplete success.
3. Save ordered native-resolution frames and metadata. Compare reported dimensions with the captured file dimensions and check for missing, extra or blank frames. Review early, middle, and late frames, plus cuts and transitions. Capture separate production screenshots for checking gameplay HUD or effects excluded from the reel.
4. Encode an explicit frame clock, flush packets and validate decoded presentation timestamps, dimensions, frame count and duration. Exercise MIME type, byte ranges and actual seeks on the output. Compare visibly distinct frames in the target browser. Label the audio contract. The sample encoder produces silent H.264 MP4 and requires a Chromium build with H.264 support.

## Runnable sample

Run the [playable fixture capture](../../full-stack-app-creation/references/cinematic-presentation.md#isolated-reproduction) in isolated storage. Its capture emits `timeline.json` with positive integers `width`, `height`, `fps`, and `count` plus numbered `frame-0000.png` files from tick zero. The sample expects even frame dimensions and at least four frames of visible content.

Install the [pinned media dependencies](../assets/code-video/requirements.txt) in a virtual environment and discover an installed Chromium executable with H.264 support. From a copy of the [code-video assets](../assets/code-video), run:

```sh
python browser_reel.py <frames-directory> <fresh-output-directory> --chrome <browser-executable>
```

The helper verifies the exact ordered sequence, encodes it with PyAV and libx264, then checks the resulting MP4 through loopback HTTP and native browser seeks. Retain `reel.mp4` and `verification.json` with the frame manifest outside the skill. An application's public download/player path requires its own integration test.

See [capture comparison and resource disposition](../../full-stack-app-creation/references/cinematic-capture-provenance.md).
