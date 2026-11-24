"""Score how Face Swap outputs treat the mouth on a synthetic expression clip.

For each expression phase it reports, in mean absolute 8-bit difference from
the original frame:
- interior: teeth, cavity and tongue inside the lips (lower is better; the
  performer's own mouth should be kept),
- tongue: the part of a stuck-out tongue (lower is better),
- lips: how much the lips changed (the swap should still replace them).
It also reports how closely frame-to-frame change around the mouth follows the
original ("motion mismatch", lower is better), which shows lagging or
smeared mouth movement.

Usage: mouth_expression_benchmark.py <clip.mp4> <swap-output-dir> [...]
The clip and its .truth.npz come from make_expression_face_clip.py. Each
output directory holds the face-swap.mp4 written by tools/face_swap_video.py.
"""
import json
from pathlib import Path
import sys

import av
import cv2
import numpy as np

from make_expression_face_clip import FPS


def frames(path):
    with av.open(str(path)) as movie:
        return np.stack([frame.to_ndarray(format="bgr24").astype(np.float32) for frame in movie.decode(video=0)])


def phase(index, smile, opening, tongue):
    if tongue > .5:
        return "tongue"
    if opening > 20:
        return "open"
    if index/FPS >= 3.1:
        return "talk"
    return "smile" if smile > .5 else "neutral"


def score(original, output, truth):
    shrink = lambda mask: cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    phases = {}
    for index, (before, after) in enumerate(zip(original, output)):
        difference = np.abs(before-after).mean(axis=2)
        row = phases.setdefault(phase(index, *truth["expression"][index]), {"interior": [], "tongue": [], "lips": []})
        for key in ("interior", "tongue"):
            mask = shrink(truth[key][index])
            if mask.any():
                row[key].append(float(difference[mask].mean()))
        row["lips"].append(float(difference[truth["lips"][index]].mean()))
    region = np.any(truth["interior"] | truth["lips"], axis=0)
    region = cv2.dilate(region.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    change = lambda clip: np.abs(np.diff(clip, axis=0)).mean(axis=3)[:, region]
    return {"phases": {name: {key: round(float(np.mean(values)), 2) if values else None for key, values in row.items()}
                       for name, row in phases.items()},
            "motion_mismatch": round(float(np.abs(change(output)-change(original)).mean()), 3)}


def main(clip, *outputs):
    clip = Path(clip)
    truth = np.load(clip.with_suffix(".truth.npz"))
    original = frames(clip)
    print(json.dumps({Path(output).name: score(original, frames(Path(output)/"face-swap.mp4"), truth)
                      for output in outputs}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
