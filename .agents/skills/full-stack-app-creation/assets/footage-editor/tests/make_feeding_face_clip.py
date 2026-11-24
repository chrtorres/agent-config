"""Make a synthetic eating clip from a still portrait, with exact occluder masks.

A hand rises from below holding a piece of food, brings it to the opening
mouth, holds it at the lips, then withdraws while the mouth chews. The hand
covers the chin and lower lip on the way, so a face swap must leave it and
the food untouched. Beside the clip, a .truth.npz holds per-frame masks of the
hand and food together ("occluder") and of the visible lips, in frame
coordinates.

Usage: make_feeding_face_clip.py <portrait-image> <output.mp4> [--mouth X Y]
The default mouth centre matches the bundled fictional portrait generator.
"""
import argparse
import math
from pathlib import Path

import av
import cv2
import numpy as np

from make_expression_face_clip import FPS, SCALE, draw_mouth, head_motion

FRAMES = 96
HAND, HAND_SHADE, FOOD, FOOD_CRUMB = (150, 175, 214), (118, 140, 185), (60, 150, 205), (40, 100, 160)


def timeline(index):
    """Food position as a fraction of the way to the mouth, and mouth opening."""
    t = index/FPS
    ramp = lambda a, b: min(1., max(0., (t-a)/(b-a)))
    reach = ramp(.5, 1.4)*(1-ramp(1.9, 2.6))
    opening = 22*ramp(.9, 1.3)*(1-ramp(1.75, 1.95))
    if t >= 1.95:  # chewing
        opening = 7*abs(math.sin(2*math.pi*1.6*(t-1.95)))
    return reach, opening


def draw_hand(canvas, mask, mouth, reach, height):
    """Draw a fist holding food on a SCALE-times canvas, food tip at the mouth when reach is 1."""
    s = lambda value: int(round(value*SCALE))
    tip = (mouth[0]+4, mouth[1]-2+(1-reach)*(height-mouth[1]+60))
    food_center = (tip[0], tip[1]+2)
    hand_center = (tip[0]+6, tip[1]+28)
    for target, food, hand, shade in ((canvas, FOOD, HAND, HAND_SHADE), (mask, 255, 255, 255)):
        cv2.ellipse(target, (s(food_center[0]), s(food_center[1])), (s(17), s(11)), -8, 0, 360, food, -1, cv2.LINE_AA)
        # Forearm, palm and four curled fingers.
        cv2.line(target, (s(hand_center[0]+10), s(hand_center[1]+10)), (s(hand_center[0]+40), s(height+80)),
                 shade, s(34), cv2.LINE_AA)
        cv2.ellipse(target, (s(hand_center[0]), s(hand_center[1])), (s(28), s(24)), 10, 0, 360, hand, -1, cv2.LINE_AA)
        for finger in range(4):
            x = hand_center[0]-20+finger*12
            cv2.ellipse(target, (s(x), s(hand_center[1]-20)), (s(7), s(11)), 0, 0, 360, shade, -1, cv2.LINE_AA)
            cv2.ellipse(target, (s(x), s(hand_center[1]-21)), (s(5.5), s(9)), 0, 0, 360, hand, -1, cv2.LINE_AA)
        cv2.ellipse(target, (s(hand_center[0]+26), s(hand_center[1]-6)), (s(8), s(16)), -30, 0, 360, hand, -1, cv2.LINE_AA)
    for dot in range(5):
        cv2.circle(canvas, (s(food_center[0]-10+dot*5), s(food_center[1]-2+(dot % 2)*4)), s(1.5), FOOD_CRUMB, -1, cv2.LINE_AA)


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
    skin = np.median(still[int(center[1])-40:int(center[1])-28, int(center[0])-30:int(center[0])+30].reshape(-1, 3), 0)
    cover = np.zeros(still.shape[:2], np.float32)
    cv2.ellipse(cover, (int(center[0]), int(center[1])), (46, 22), 0, 0, 360, 1, -1)
    cover = cv2.GaussianBlur(cover, (0, 0), 3)[..., None]
    base = (still*(1-cover)+skin*cover).astype(np.uint8)
    occluders, lips = [], []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(args.output), "w") as movie:
        stream = movie.add_stream("libx264", rate=FPS, options={"crf": "12"})
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        for index in range(FRAMES):
            reach, opening = timeline(index)
            drawn, (_, _, lip_mask) = draw_mouth(base, center, skin, 0., opening, 0.)
            big = cv2.resize(drawn, (width*SCALE, height*SCALE), interpolation=cv2.INTER_CUBIC)
            hand = np.zeros(big.shape[:2], np.uint8)
            if reach > 0:
                draw_hand(big, hand, center, reach, height)
            drawn = cv2.resize(cv2.GaussianBlur(big, (0, 0), SCALE*.6), (width, height), interpolation=cv2.INTER_AREA)
            hand = cv2.resize(hand, (width, height), interpolation=cv2.INTER_AREA) > 127
            dx, dy, roll = head_motion(index)
            matrix = cv2.getRotationMatrix2D((width/2, height/2), roll, 1)
            matrix[:, 2] += (dx, dy)
            frame = cv2.warpAffine(drawn, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            warp = lambda mask: cv2.warpAffine(mask.astype(np.uint8), matrix, (width, height), flags=cv2.INTER_NEAREST) > 0
            occluders.append(warp(hand))
            lips.append(warp(lip_mask & ~hand))
            for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="bgr24")):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)
    np.savez_compressed(args.output.with_suffix(".truth.npz"), occluder=np.stack(occluders), lips=np.stack(lips),
                        reach=np.float32([timeline(index)[0] for index in range(FRAMES)]))


if __name__ == "__main__":
    main()
