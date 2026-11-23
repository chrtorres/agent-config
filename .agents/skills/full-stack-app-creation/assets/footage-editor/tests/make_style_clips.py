"""Make synthetic clips in known recording styles for the style tools' tests.

Each clip films a procedurally drawn scene (coloured shapes, texture and a
sliding camera) through one of a few made-up "cameras". A camera fixes the
frame size, frame rate, bitrate and keyframe interval, a colour grade
(curve, cast, saturation), vignette, softness, grain and handheld shake, and
the room sound (loudness and tonal balance). The same camera with a different
scene seed is the same recording style with different content.

Usage: make_style_clips.py <output-directory>
Writes <camera>-<scene>[b].mp4 for each entry in CLIPS; a "b" clip is a later
part of the same shoot (same scene and camera, the camera further along).
"""
from fractions import Fraction
import math
from pathlib import Path
import sys

import av
import cv2
import numpy as np

CAMERAS = {
    # Warm, contrasty, grainy handheld at 24 fps with a heavy vignette and boomy sound.
    "film": {"size": (960, 540), "fps": 24, "bitrate": 2.5e6, "gop": 24, "gamma": .85, "contrast": 1.25,
             "cast": (1.08, 1., .84), "saturation": 1.15, "vignette": .35, "blur": .6, "grain": 6., "grain_size": 1.,
             "shake": 5., "roll": .5, "loudness": -18, "low": 2.5, "high": .4},
    # Cool, flat, clean, locked-off 30 fps with bright thin sound.
    "studio": {"size": (640, 480), "fps": 30, "bitrate": 4e6, "gop": 60, "gamma": 1.1, "contrast": .8,
               "cast": (.9, 1., 1.12), "saturation": .8, "vignette": 0., "blur": 0., "grain": 0., "grain_size": 0.,
               "shake": 0., "roll": 0., "loudness": -28, "low": .5, "high": 2.},
}
# (camera, scene seed, part): part 1 continues the same shoot as part 0.
CLIPS = [("film", 1, 0), ("film", 1, 1), ("film", 2, 0), ("studio", 3, 0)]
SECONDS = 3.


def scene(seed, size):
    """A large canvas of shapes and texture the camera slides across."""
    rng = np.random.default_rng(seed)
    width, height = size[0]*2, size[1]*2
    canvas = np.zeros((height, width, 3), np.float32)
    # Mostly neutral surfaces (walls, floor) with some coloured objects, like most real scenes.
    top, bottom = rng.uniform(110, 170), rng.uniform(80, 140)
    canvas[:] = np.linspace(top, bottom, height)[:, None, None]*(1+rng.uniform(-.015, .015, 3))
    for _ in range(90):
        grey = rng.uniform(20, 235)
        colour = grey+(rng.uniform(-60, 60, 3) if rng.random() < .4 else rng.uniform(-6, 6, 3))
        x, y = int(rng.uniform(0, width)), int(rng.uniform(0, height))
        r = int(rng.uniform(10, 90))
        if rng.random() < .5:
            cv2.circle(canvas, (x, y), r, colour.tolist(), -1, cv2.LINE_AA)
        else:
            cv2.rectangle(canvas, (x, y), (x+r, y+int(rng.uniform(10, 90))), colour.tolist(), -1, cv2.LINE_AA)
    texture = cv2.GaussianBlur(rng.normal(0, 10, (height, width)).astype(np.float32), (0, 0), 2)
    return np.clip(canvas+texture[..., None], 0, 255)


def grade(rgb, camera, vignette):
    image = rgb/255
    image = np.clip(.5+(image**camera["gamma"]-.5)*camera["contrast"], 0, 1)
    image = image*np.float32(camera["cast"])
    gray = image.mean(axis=2, keepdims=True)
    image = gray+(image-gray)*camera["saturation"]
    image = image*vignette[..., None]
    out = np.clip(image, 0, 1)*255
    if camera["blur"]:
        out = cv2.GaussianBlur(out, (0, 0), camera["blur"])
    return out


def shake_path(rng, frames, fps, amplitude, roll):
    noise = rng.normal(0, 1, (frames+40, 3))
    kernel = np.exp(-.5*(np.arange(-6, 7)/2.)**2)
    shaped = np.stack([np.convolve(noise[:, k], kernel/kernel.sum(), "same") for k in range(3)], 1)[20:20+frames]
    shaped /= np.maximum(shaped.std(axis=0), 1e-9)
    return shaped[:, 0]*amplitude, shaped[:, 1]*amplitude, shaped[:, 2]*roll


def room_sound(rng, seconds, camera, rate=48000):
    t = np.arange(int(seconds*rate))/rate
    voice = sum(np.sin(2*math.pi*f*t+rng.uniform(0, 6))*a for f, a in ((180, .5), (360, .3), (900, .2), (2400, .12)))
    voice *= .5+.5*np.sin(2*math.pi*3*t)**2
    noise = rng.normal(0, .05, len(t))
    from scipy.signal import butter, sosfilt
    low = sosfilt(butter(2, 250/(rate/2), "low", output="sos"), voice+noise)
    high = sosfilt(butter(2, 4000/(rate/2), "high", output="sos"), voice+noise)
    mid = voice+noise-low-high
    signal = low*camera["low"]+mid+high*camera["high"]
    rms = math.sqrt((signal**2).mean())
    return (signal*10**(camera["loudness"]/20)/rms).astype(np.float32), rate


def make(path, camera_name, seed, part=0):
    camera = CAMERAS[camera_name]
    rng = np.random.default_rng(seed*7+1+part*1000)
    width, height = camera["size"]
    fps = camera["fps"]
    frames = int(SECONDS*fps)
    canvas = scene(seed, camera["size"])
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    radius = np.hypot((x-width/2)/(width/2), (y-height/2)/(height/2))/math.sqrt(2)
    vignette = 1-camera["vignette"]*radius**2
    dx, dy, roll = shake_path(rng, frames, fps, camera["shake"], camera["roll"])
    sound, rate = room_sound(rng, SECONDS, camera)
    with av.open(str(path), "w") as movie:
        stream = movie.add_stream("libx264", rate=fps, options={"g": str(camera["gop"]), "bf": "2", "preset": "fast"})
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        stream.bit_rate = int(camera["bitrate"])
        audio = movie.add_stream("aac", rate=rate)
        audio.layout = "mono"
        audio.bit_rate = 128000
        for index in range(frames):
            pan = (index/frames+part)/2
            centre = (width*(.6+.8*pan)+dx[index], height*(.8+.3*math.sin(pan*3))+dy[index])
            matrix = cv2.getRotationMatrix2D(centre, roll[index], 1.)
            matrix[:, 2] += (width/2-centre[0], height/2-centre[1])
            view = cv2.warpAffine(canvas, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            image = grade(view, camera, vignette)
            if camera["grain"]:
                grain = rng.normal(0, 1, (height, width)).astype(np.float32)
                if camera["grain_size"]:
                    grain = cv2.GaussianBlur(grain, (0, 0), camera["grain_size"])
                    grain /= grain.std()
                image = image+grain[..., None]*camera["grain"]
            frame = av.VideoFrame.from_ndarray(np.clip(np.rint(image), 0, 255).astype(np.uint8), format="rgb24")
            for packet in stream.encode(frame):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)
        for offset in range(0, len(sound), 1024):
            chunk = av.AudioFrame.from_ndarray(sound[None, offset:offset+1024].copy(), format="fltp", layout="mono")
            chunk.sample_rate, chunk.pts = rate, offset
            for packet in audio.encode(chunk):
                movie.mux(packet)
        for packet in audio.encode():
            movie.mux(packet)


def main(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for camera, seed, part in CLIPS:
        make(directory/f"{camera}-{seed}{'abc'[part] if part else ''}.mp4", camera, seed, part)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
