"""Fit a frame-aligned camera-plane rig and write foreground masks."""
import argparse
import json
from pathlib import Path
import tempfile

import av
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image

from measure_motion import world_frame, world_track, write_json
from progress import Progress, frame_total

SCALE = 5
GRID = 4
LANDMARKS = (0, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)


class InsufficientPose(ValueError):
    pass


def track(source, model, include_world=False):
    vision = mp.tasks.vision
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.3,
        min_tracking_confidence=0.4,
        output_segmentation_masks=True,
    )
    masks, poses, timestamps, world = [], [], [], []
    with av.open(str(source)) as container, vision.PoseLandmarker.create_from_options(options) as detector:
        playback_origin = (container.start_time or 0) / av.time_base
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if include_world else None
        width, height = stream.width, stream.height
        tile = ((width + SCALE - 1) // SCALE, (height + SCALE - 1) // SCALE)
        stream.codec_context.thread_count = 3
        progress = Progress(frame_total(stream))
        for index, frame in enumerate(container.decode(stream)):
            timestamp = frame.pts * frame.time_base
            rgb = frame.to_ndarray(format="rgb24")
            fitted = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                                               int((timestamp - (timestamps[0] if timestamps else timestamp)) * 1000))
            if include_world:
                # Keep raw frame-aligned depth. Gap filling and smoothing below apply to the 2D rig only.
                world.append(world_frame(fitted))
            if fitted.pose_landmarks and fitted.segmentation_masks:
                joints = fitted.pose_landmarks[0]
                poses.append([[joints[i].x*width, joints[i].y*height, joints[i].visibility] for i in LANDMARKS])
                matte = cv2.resize(fitted.segmentation_masks[0].numpy_view(), tile, interpolation=cv2.INTER_AREA)
                # Drop low-confidence speckling while leaving a feathered
                # silhouette for hair and clothing that meet the background.
                masks.append(np.rint(np.clip((matte-.16)/.72, 0, 1)*255).astype(np.uint8))
            else:
                poses.append(None)
                masks.append(None)
            timestamps.append(timestamp)
            progress.update(index + 1)
            if index % 150 == 0:
                print(f"Tracking frame {index}", flush=True)
    coverage = sum(p is not None for p in poses)
    if not coverage or coverage < len(masks)*.85:
        raise InsufficientPose("Insufficient pose detections for this recording")
    valid = np.flatnonzero([p is not None for p in poses])
    for i in np.flatnonzero([p is None for p in poses]):
        nearest = min(valid, key=lambda j: abs(i-j))
        poses[i], masks[i] = poses[nearest], masks[nearest]
    points = np.asarray(poses)
    # Smooth frame-to-frame detector jitter without retiming the decoded video.
    smoothed = points.copy()
    smoothed[1:-1, :, :2] = .19*points[:-2, :, :2] + .62*points[1:-1, :, :2] + .19*points[2:, :, :2]
    return (width, height), tile, masks, smoothed, timestamps, coverage, world_track(fps, world), playback_origin


def write_atlases(staging, masks, tile):
    width, height = tile
    pages = []
    pixel_count = GRID*GRID
    for i, mask in enumerate(masks):
        slot = i % pixel_count
        if not slot:
            atlas = np.zeros((height*GRID, width*GRID, 3), np.uint8)
        x, y = slot % GRID * width, slot // GRID * height
        atlas[y:y+height,x:x+width,0] = mask
        if slot == pixel_count-1 or i == len(masks)-1:
            name = f"matte-{len(pages):03d}.png"
            Image.fromarray(atlas).save(staging/name,compress_level=3)
            pages.append([name])
    return pages


def build(source, model, output, world=None):
    cv2.setNumThreads(2)
    (width, height), tile, masks, points, timestamps, coverage, depth, playback_origin = track(source, model, world is not None)
    if len(timestamps) < 2:
        raise ValueError("Motion tools require at least two video frames.")
    if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
        raise ValueError("Motion tools require increasing frame timestamps.")
    period = (timestamps[-1] - timestamps[0]) / (len(timestamps)-1)
    variable = any(t != timestamps[0]+i*period for i, t in enumerate(timestamps))
    output.mkdir(parents=True, exist_ok=True)
    target = output / "timeline"
    if target.exists():
        raise FileExistsError(f"Choose a new output directory: {target} exists")
    with tempfile.TemporaryDirectory(dir=output) as scratch:
        staging = Path(scratch) / "timeline"
        staging.mkdir()
        pages = write_atlases(staging, masks, tile)
        quantized = np.rint(points * [4, 4, 100]).astype(int)
        manifest = {
            "fps": float(1/period), "height": height, "tile": tile, "grid": GRID,
            # Workers use the container clock; the browser uses media time relative to its origin.
            "presentationStart": float(timestamps[0]),
            "playbackStart": max(0., float(timestamps[0]) - playback_origin),
            "landmarks": LANDMARKS, "pixelScale": SCALE, "pages": pages,
            "frames": [[width, [p.tolist()]] for p in quantized],
            "shots": [[0, len(masks)]], "protected": [[0, 0, 0, 0]],
            "reflection": [[0, 0, width, height]],
            "travelY": [[height*.50, height*.83]],
            "rootLimit": [width*.19, height*.073],
            "identityPreview": True,
        }
        if variable:
            manifest["frameTimes"] = [float(t - timestamps[0]) for t in timestamps]
        (staging/"timeline.json").write_text(json.dumps(manifest, separators=(",", ":")))
        staging.rename(target)
    if world is not None:
        depth["fps"] = manifest["fps"]
        write_json(depth, world)
    print(json.dumps({"tracked_frames": coverage, "frame_count": len(masks),
                      "landmarks_per_frame": len(LANDMARKS), "atlas_pages": len(pages)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--world", type=Path, help="Write monocular depth from the same inference pass")
    args = parser.parse_args()
    try:
        build(args.source, args.model, args.output, args.world)
    except InsufficientPose:
        parser.exit(3, "Insufficient pose detections for this recording.\n")
