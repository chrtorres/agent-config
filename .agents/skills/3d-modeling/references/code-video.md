# Code-generated video

1. Establish the intended artifact and acceptance criteria before implementation. For an authored video, specify resolution, rational frame rate, duration, camera, pose timing, color, codecs and audio. When a reference is available, define how to measure alignment and tolerances at the frame and sample levels. Only use supplied media as input when the user authorizes it.
2. Generate the imagery from Python or a scripted Blender scene. Use integer frame indexes and a rational time base. Evaluate animation, camera and cuts on that clock. Render zero-padded frame files with explicit dimensions. For sound, compute sample positions from the same timeline and carry oscillator or envelope state across blocks.
3. Encode with explicit video and audio formats and flush both encoders. For browser delivery, test the chosen codecs, seeking, metadata, media requests and native controls in the intended browser. Keep frames, sidecar data, and rendered evidence in the task directory.
4. For recorded media preservation, extract or demux the authorized input at run time. Preserve codec configuration, encoded samples, decode and presentation timing, sync samples, edit lists and audio priming. Remux first and compare the complete streams. When the requirement is exact file bytes, also compare full hashes or bytes. Exact container reproduction may require writing original box ordering, metadata, chunk layout, offsets and padding. An identical decoded result establishes media equality. Rendering a new scene requires its own visual acceptance criteria. [MP4 sample and track structures](https://developer.apple.com/documentation/quicktime-file-format), [AAC priming and edits](https://developer.apple.com/documentation/quicktime-file-format/using_track_structures_to_represent_encode_delay_explicitly).
5. Compare decoded frame counts, geometry, timing, motion, and audio before delivery. Inspect representative rendered frames. For a reference-preserving task, additionally compare encoded packet data, decoded image planes and audio samples, and exact rational timestamps. A browser screenshot is evidence for the sampled display state. A source hash identifies the build input.
6. Retain only reusable logic and synthetic input in the shared skill. A packet dump, imported media module, frame grab, embedded thumbnail, contact sheet, manifest hash, transcript or metadata can expose the original recording. Regenerate these from synthetic input for shared documentation or validation.

## Run the synthetic example

Use Python 3.10+ with the pinned dependencies in [requirements.txt](../assets/code-video/requirements.txt). The PyAV build needs libx264 and AAC support. Blender with Workbench and a Chromium-compatible browser with H.264 support are needed for the complete smoke test. Copy [code-video](../assets/code-video/) to an empty retained sandbox and run from the copy. Substitute runtime-discovered executable names where needed.

```sh
python3 -m pip install -r requirements.txt
python3 -B video.py generate procedural.mp4
python3 -B video.py remux procedural.mp4 remuxed.mp4
python3 -B video.py inspect procedural.mp4 --compare remuxed.mp4
blender -b --factory-startup --python-exit-code 1 --python blender_frames.py -- frames
python3 -B video.py generate spatial.mp4 --frames-dir frames
python3 -B smoke.py --frames-dir frames --output evidence --chrome <chromium-executable>
```

Use an isolated Python environment for installation. The smoke output directory must be new. The standalone generator draws a geometric 2D scene, creates an audio tone, and encodes MP4. The Blender script generates a rotating and translating cube. The remux example supports one compatible video and one audio track. The comparator checks packet bytes and timing, decoded RGB pixels and audio, and reports container-byte equality independently. Use native decoded planes for acceptance criteria that require exact YUV equality. The loopback browser harness is for fixture review and tests byte ranges, seeking, display changes and playback. Apply the normal interactive 3D review when delivering a new model.
