"""Make a synthetic action clip from a still portrait, with exact ground truth.

The portrait is moved through a pause, a whip pan, a fast shake with roll,
a quick zoom, a horizontal squash that imitates a head turn, and a blurred
diagonal whip. Each frame integrates eight sub-frame renders across a 180°
shutter, so fast segments carry real motion blur. The 2x3 matrix that maps
still-image coordinates into each frame (at mid-exposure) is written beside
the clip, so tracking can be scored against the true position.

Usage: make_action_face_clip.py <portrait-image> <output.mp4>
"""
import json
import math
from pathlib import Path
import sys

import av
import cv2
import numpy as np

WIDTH, HEIGHT, FPS, FRAMES, SUBFRAMES = 640, 480, 30, 96, 8


def pose(t):
    """Center offset, roll in degrees, scale, and horizontal squash at time t (frames)."""
    x, y, roll, scale, squash = 0., 0., 0., .62, 1.
    if t >= 10:  # whip pan right and back
        p = min(1, (t-10)/14)
        x += 150*math.sin(math.pi*p)
    if 26 <= t < 46:  # shake with roll at 6 Hz
        p = (t-26)/FPS
        envelope = math.sin(math.pi*(t-26)/20)
        x += 38*math.sin(2*math.pi*6*p)*envelope
        y += 22*math.sin(2*math.pi*4.5*p+1)*envelope
        roll += 16*math.sin(2*math.pi*3*p)*envelope
    if t >= 46:  # quick zoom in, then out
        scale *= 1+.45*math.sin(math.pi*min(1, (t-46)/16))
    if 62 <= t < 78:  # head-turn-like squash
        squash = 1-.3*math.sin(math.pi*(t-62)/16)
        x += -30*math.sin(math.pi*(t-62)/16)
    if t >= 78:  # blurred diagonal whip
        p = min(1, (t-78)/12)
        x += -170*math.sin(math.pi*p)
        y += 70*math.sin(math.pi*p)
        roll += -12*math.sin(math.pi*p)
    return x, y, roll, scale, squash


def matrix(t, size):
    x, y, roll, scale, squash = pose(t)
    w, h = size
    angle = math.radians(roll)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    linear = rotation @ np.diag([scale*squash, scale])
    center = np.array([WIDTH/2+x, HEIGHT/2+y])
    offset = center-linear @ np.array([w/2, h/2])
    return np.hstack([linear, offset[:, None]])


def main(portrait, output):
    image = cv2.imread(str(portrait))
    if image is None:
        raise SystemExit("The portrait could not be read.")
    size = image.shape[1], image.shape[0]
    background = tuple(int(v) for v in image[4, 4])
    truth = []
    with av.open(str(output), "w") as movie:
        stream = movie.add_stream("libx264", rate=FPS, options={"crf": "14"})
        stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
        for index in range(FRAMES):
            accumulated = np.zeros((HEIGHT, WIDTH, 3), np.float32)
            for sub in range(SUBFRAMES):
                t = index-.25+.5*(sub+.5)/SUBFRAMES
                accumulated += cv2.warpAffine(image, matrix(t, size), (WIDTH, HEIGHT), flags=cv2.INTER_CUBIC,
                                              borderMode=cv2.BORDER_CONSTANT, borderValue=background)
            frame = np.rint(accumulated/SUBFRAMES).astype(np.uint8)
            truth.append(matrix(index, size).tolist())
            video = av.VideoFrame.from_ndarray(frame, format="bgr24")
            video.pts = index
            for packet in stream.encode(video):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)
    Path(output).with_suffix(".truth.json").write_text(json.dumps({"fps": FPS, "matrices": truth}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
