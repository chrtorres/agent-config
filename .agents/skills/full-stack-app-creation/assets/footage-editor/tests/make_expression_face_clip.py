"""Make a synthetic expression clip from a still portrait, with exact mouth masks.

The portrait's mouth is repainted every frame through a neutral hold, a smile
that shows teeth, a wide open mouth, a tongue pushed out over the lower lip
and chin, and fast talking. The head drifts and rolls slightly throughout.
Beside the clip, a .truth.npz holds per-frame masks of the mouth interior
(teeth, tongue and the dark mouth cavity), the tongue alone and the lips, in
frame coordinates, so a face swap can be scored on how it treats each part.

Usage: make_expression_face_clip.py <portrait-image> <output.mp4> [--mouth X Y]
The default mouth centre matches the bundled fictional portrait generator.
"""
import argparse
import math
from pathlib import Path

import av
import cv2
import numpy as np

FPS, FRAMES, SCALE = 30, 120, 3
LIP, CAVITY, TEETH, TONGUE = (82, 89, 160), (34, 22, 52), (222, 232, 240), (112, 104, 214)


def expression(index):
    """Smile 0..1, opening in pixels, tongue 0..1 at a frame."""
    t = index/FPS
    ramp = lambda a, b: min(1., max(0., (t-a)/(b-a)))
    smile = ramp(.5, 1.1)*(1-ramp(1.4, 1.6))
    opening = 30*ramp(1.5, 1.9)*(1-ramp(2.9, 3.1))
    tongue = ramp(2.0, 2.3)*(1-ramp(2.6, 2.9))
    if t >= 3.1:  # talking at about 4 syllables a second with a slight smile
        opening = 16*abs(math.sin(2*math.pi*2*(t-3.1)))
        smile = .3
    return smile, opening, tongue


def mouth_shapes(center, smile, opening, tongue):
    """Polygons (outer lips, inner opening) and a tongue ellipse, in pixels."""
    cx, cy = center
    half = 36+9*smile
    corner = -7*smile
    opening = max(opening, 6*smile)
    u = np.linspace(-1, 1, 41)
    arch = np.sqrt(np.clip(1-u**2, 0, 1))
    x = cx+half*u
    upper_inner = cy+corner*(1-arch)-opening*.3*arch
    lower_inner = cy+corner*(1-arch)+opening*.7*arch**.8
    upper_outer = upper_inner-7*arch-1
    lower_outer = lower_inner+9*arch+1
    outer = np.r_[np.c_[x, upper_outer], np.c_[x, lower_outer][::-1]]
    inner = np.r_[np.c_[x, upper_inner], np.c_[x, lower_inner][::-1]]
    ellipse = None
    if tongue > .02:
        ellipse = ((cx, cy+opening*.55+20*tongue), (15, 9+19*tongue))
    return outer, inner, ellipse, opening


def draw_mouth(image, center, skin, smile, opening, tongue):
    """Repaint the mouth on a SCALE-times canvas. Returns (image, masks)."""
    height, width = image.shape[:2]
    big = cv2.resize(image, (width*SCALE, height*SCALE), interpolation=cv2.INTER_CUBIC)
    outer, inner, ellipse, opening = mouth_shapes(center, smile, opening, tongue)
    s = lambda points: np.rint(points*SCALE).astype(np.int32)
    interior, tongue_mask, lips = (np.zeros(big.shape[:2], np.uint8) for _ in range(3))
    cv2.fillPoly(big, [s(outer)], LIP, cv2.LINE_AA)
    cv2.fillPoly(lips, [s(outer)], 255)
    if opening > .5:
        cv2.fillPoly(big, [s(inner)], CAVITY, cv2.LINE_AA)
        cv2.fillPoly(interior, [s(inner)], 255)
        # Upper teeth follow the top of the opening.
        teeth = np.zeros_like(interior)
        top = inner[:41].copy()
        band = np.r_[top, (top+[0, min(9, .45*opening)])[::-1]]
        cv2.fillPoly(teeth, [s(band)], 255)
        teeth &= interior
        big[teeth > 0] = TEETH
        if opening > 8:
            cv2.ellipse(big, (int(center[0]*SCALE), int((center[1]+opening*.55)*SCALE)),
                        (int(22*SCALE), int(opening*.2*SCALE)), 0, 180, 360, TONGUE, -1, cv2.LINE_AA)
    if ellipse is not None:
        (ex, ey), (ax, ay) = ellipse
        cv2.ellipse(big, (int(ex*SCALE), int(ey*SCALE)), (int(ax*SCALE), int(ay*SCALE)), 0, 0, 360, TONGUE, -1, cv2.LINE_AA)
        cv2.ellipse(tongue_mask, (int(ex*SCALE), int(ey*SCALE)), (int(ax*SCALE), int(ay*SCALE)), 0, 0, 360, 255, -1)
        cv2.line(big, (int(ex*SCALE), int((ey-ay*.6)*SCALE)), (int(ex*SCALE), int((ey+ay*.5)*SCALE)),
                 (90, 80, 180), SCALE, cv2.LINE_AA)
    interior |= tongue_mask
    lips &= ~interior
    small = lambda mask: cv2.resize(mask, (width, height), interpolation=cv2.INTER_AREA) > 127
    image = cv2.resize(cv2.GaussianBlur(big, (0, 0), SCALE*.9), (width, height), interpolation=cv2.INTER_AREA)
    return image, (small(interior), small(tongue_mask), small(lips))


def head_motion(index):
    t = index/FPS
    return 14*math.sin(2*math.pi*.4*t), 6*math.sin(2*math.pi*.7*t+.5), 4*math.sin(2*math.pi*.5*t)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("portrait", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--mouth", type=float, nargs=2, default=(240., 352.))
    args = cli.parse_args()
    still = cv2.imread(str(args.portrait))
    height, width = still.shape[:2]
    width, height = width//2*2, height//2*2
    still = still[:height, :width]
    center = np.float32(args.mouth)
    # Clear the original mouth with surrounding skin so it can be redrawn.
    skin = np.median(still[int(center[1])-40:int(center[1])-28, int(center[0])-30:int(center[0])+30].reshape(-1, 3), 0)
    base = still.copy()
    cover = np.zeros(still.shape[:2], np.float32)
    cv2.ellipse(cover, (int(center[0]), int(center[1])), (46, 22), 0, 0, 360, 1, -1)
    cover = cv2.GaussianBlur(cover, (0, 0), 3)[..., None]
    base = (base*(1-cover)+skin*cover).astype(np.uint8)
    masks = {"interior": [], "tongue": [], "lips": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(args.output), "w") as movie:
        stream = movie.add_stream("libx264", rate=FPS, options={"crf": "12"})
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        for index in range(FRAMES):
            drawn, (interior, tongue, lips) = draw_mouth(base, center, skin, *expression(index))
            dx, dy, roll = head_motion(index)
            matrix = cv2.getRotationMatrix2D((width/2, height/2), roll, 1)
            matrix[:, 2] += (dx, dy)
            frame = cv2.warpAffine(drawn, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            for key, mask in zip(masks, (interior, tongue, lips)):
                masks[key].append(cv2.warpAffine(mask.astype(np.uint8), matrix, (width, height), flags=cv2.INTER_NEAREST) > 0)
            for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="bgr24")):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)
    phases = [expression(index) for index in range(FRAMES)]
    np.savez_compressed(args.output.with_suffix(".truth.npz"), **{key: np.stack(value) for key, value in masks.items()},
                        expression=np.float32(phases))


if __name__ == "__main__":
    main()
