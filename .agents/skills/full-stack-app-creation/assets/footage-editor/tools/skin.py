"""Prepare soft skin and hair masks for the interactive color controls.

Each atlas page is RGB: red holds skin weight, green holds hair weight.
"""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from queue import SimpleQueue
import tempfile

import av
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
from media import presentation_offset
from progress import Progress


def segmenter_workers():
    # Each segmenter runs single-threaded inference, so a few instances in parallel
    # use otherwise idle cores while preparation's other workers keep running.
    return max(1, min(4, (os.cpu_count() or 2) // 3))


def build(source, model, timeline, output):
    manifest = json.loads(timeline.read_text())
    tw, th = manifest["tile"]
    grid = manifest["grid"]
    slots = grid**2
    output.mkdir(parents=True, exist_ok=True)
    vision = mp.tasks.vision
    # IMAGE mode gives the same masks as VIDEO mode for this segmenter (it keeps no temporal
    # state), which lets independent instances process frames out of order.
    options = vision.ImageSegmenterOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.IMAGE,
        output_confidence_masks=True,
    )
    cv2.setNumThreads(2)
    workers = segmenter_workers()
    detectors = [vision.ImageSegmenter.create_from_options(options) for _ in range(workers)]
    idle = SimpleQueue()
    for detector in detectors:
        idle.put(detector)

    def skin_weight(preview):
        detector = idle.get()
        try:
            masks = detector.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=preview)).confidence_masks
            skin = masks[2].numpy_view() + masks[3].numpy_view()
            hair = np.array(masks[1].numpy_view())
        finally:
            idle.put(detector)
        weight = np.clip((skin-.61)/.32, 0, 1)
        weight = cv2.erode(weight, np.ones((3,3), np.uint8))
        # Hair keeps a softer edge so a dye fades into flyaway strands.
        hair = np.clip((hair-.45)/.35, 0, 1)
        return np.dstack([cv2.resize(weight, (tw,th), interpolation=cv2.INTER_AREA),
                          cv2.resize(hair, (tw,th), interpolation=cv2.INTER_AREA)])

    total = len(manifest["frames"])
    progress = Progress(total)
    try:
        with (tempfile.TemporaryDirectory(dir=output) as scratch,
              ThreadPoolExecutor(workers) as pool,
              av.open(str(source)) as clip):
            staging = Path(scratch)
            # Use the two semantic skin classes plus the original performer matte.
            # Clothing/hair probabilities and an eroded edge suppress color spill.
            labels = list(detectors[0].labels)
            if labels and (labels[2:4] != ["body-skin", "face-skin"] or labels[1] != "hair"):
                raise ValueError(f"Unexpected model skin classes: {labels}")
            stream = clip.streams.video[0]
            stream.codec_context.thread_count = 3
            pending = deque()
            state = {"page": None, "atlas": None, "foreground": None}

            def place(i, weight):
                slot, page = i % slots, i // slots
                if not slot:
                    state["foreground"] = np.asarray(Image.open(timeline.parent/manifest["pages"][page][0]))[:,:,0]
                    state["atlas"] = np.zeros((th*grid,tw*grid,3),np.uint8)
                atlas, foreground = state["atlas"], state["foreground"]
                x,y = slot%grid*tw,slot//grid*th
                # Hair can extend past the performer matte's soft edge, so it
                # is limited by a dilated matte rather than the matte itself.
                present = foreground[y:y+th,x:x+tw]/255
                near = cv2.dilate(present.astype(np.float32), np.ones((3,3), np.uint8))
                atlas[y:y+th,x:x+tw,0] = np.rint(weight[...,0]*present*255).astype(np.uint8)
                atlas[y:y+th,x:x+tw,1] = np.rint(weight[...,1]*near*255).astype(np.uint8)
                if slot == slots-1 or i+1 == total:
                    Image.fromarray(atlas).save(staging/f"skin-{page:03d}.png")
                progress.update(i+1)

            count = 0
            for i, frame in enumerate(clip.decode(stream)):
                count = i+1
                if count > total:
                    break
                t = max(0., float(frame.pts*frame.time_base) - manifest.get("presentationStart", 0))
                if abs(t-presentation_offset(manifest,i)) > .0006:
                    raise ValueError(f"Timeline mismatch at frame {i}")
                rgb = frame.to_ndarray(format="rgb24")
                # Reduce the confidence-mask output size without changing framing.
                preview = cv2.resize(rgb, (tw*2,th*2), interpolation=cv2.INTER_AREA)
                pending.append((i, pool.submit(skin_weight, preview)))
                # Keep a short ordered window so atlas pages are written in sequence.
                while len(pending) > workers * 3:
                    index, future = pending.popleft()
                    place(index, future.result())
            while pending:
                index, future = pending.popleft()
                place(index, future.result())
            if count != total:
                raise ValueError("Skin atlas frame count differs from timeline")
            for image in staging.glob("*.png"):
                image.replace(output/image.name)
    finally:
        for detector in detectors:
            detector.close()
    progress.finish()
    print(json.dumps({"skin_frames": count, "skin_atlas_pages":len(manifest["pages"])}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","skin_model","timeline","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    build(args.source,args.skin_model,args.timeline,args.output)
