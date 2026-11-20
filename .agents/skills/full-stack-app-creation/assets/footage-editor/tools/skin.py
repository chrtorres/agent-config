"""Prepare soft skin-only masks for the interactive color controls."""
import argparse
import json
from pathlib import Path
import tempfile

import av
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image


def build(source, model, timeline, output):
    manifest = json.loads(timeline.read_text())
    tw, th = manifest["tile"]
    grid = manifest["grid"]
    slots = grid**2
    output.mkdir(parents=True, exist_ok=True)
    vision = mp.tasks.vision
    options = vision.ImageSegmenterOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        output_confidence_masks=True,
    )
    cv2.setNumThreads(2)
    with (tempfile.TemporaryDirectory(dir=output) as scratch,
          vision.ImageSegmenter.create_from_options(options) as detector,
          av.open(str(source)) as clip):
        staging = Path(scratch)
        # Use the two semantic skin classes plus the original performer matte.
        # Clothing/hair probabilities and an eroded edge suppress color spill.
        labels = list(detector.labels)
        if labels and labels[2:4] != ["body-skin", "face-skin"]:
            raise ValueError(f"Unexpected model skin classes: {labels}")
        count = 0
        for i, frame in enumerate(clip.decode(video=0)):
            count = i+1
            t = float(frame.pts*frame.time_base)
            if abs(t-i/manifest["fps"]) > .0006:
                raise ValueError(f"Timeline mismatch at frame {i}")
            slot, page = i % slots, i // slots
            if not slot:
                foreground = np.asarray(Image.open(timeline.parent/manifest["pages"][page][0]))[:,:,0]
                atlas = np.zeros((th*grid,tw*grid),np.uint8)
            rgb = frame.to_ndarray(format="rgb24")
            # Reduce the confidence-mask output size without changing framing.
            preview = cv2.resize(rgb, (tw*2,th*2), interpolation=cv2.INTER_AREA)
            image = mp.Image(image_format=mp.ImageFormat.SRGB,data=preview)
            prediction = detector.segment_for_video(image,int(t*1000))
            masks = prediction.confidence_masks
            skin = masks[2].numpy_view() + masks[3].numpy_view()
            weight = np.clip((skin-.61)/.32, 0, 1)
            weight = cv2.erode(weight, np.ones((3,3), np.uint8))
            weight = cv2.resize(weight, (tw,th), interpolation=cv2.INTER_AREA)
            x,y = slot%grid*tw,slot//grid*th
            present = foreground[y:y+th,x:x+tw]/255
            atlas[y:y+th,x:x+tw] = np.rint(weight*present*255).astype(np.uint8)
            if slot == slots-1 or count == len(manifest["frames"]):
                Image.fromarray(atlas).save(staging/f"skin-{page:03d}.png")
        if count != len(manifest["frames"]):
            raise ValueError("Skin atlas frame count differs from timeline")
        for image in staging.glob("*.png"):
            image.replace(output/image.name)
    print(json.dumps({"skin_frames": count, "skin_atlas_pages":len(manifest["pages"])}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","skin_model","timeline","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    build(args.source,args.skin_model,args.timeline,args.output)
