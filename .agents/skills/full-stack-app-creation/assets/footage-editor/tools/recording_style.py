"""Learn a video's recording style, compare styles, and render footage in a style.

A style profile is a small JSON document of aggregate measurements. It holds
no pixels, faces or sound, only numbers that describe how the footage was
recorded and delivered:

- format: frame size and aspect, frame rate, codec, bits per pixel, keyframe
  interval, B-frames, pixel format and colour range;
- colour: the lightness distribution (101 quantiles of CIELAB L*), the colour
  cast and spread (mean and covariance of a*, b*), and saturation;
- texture: luma and chroma noise (Immerkaer's estimator on flat areas), grain
  coarseness (how much noise survives a 2x reduction) and edge sharpness
  (fine-to-coarse gradient ratio on strong edges, which noise barely moves);
- vignette: how much darker the corners are than the centre, fitted from how
  the same scenery changes brightness as the camera moves it across the frame
  (so a dark object near the edge is not mistaken for vignetting); a camera
  that never moves leaves it unmeasured;
- camera motion: handheld shake (translation and roll left after removing the
  smooth camera path), its frequency, and how fast the camera pans;
- editing: cut rate and shot length (informational, not used in matching);
- audio: loudness, peak, noise floor, low/mid/high balance, sample rate and
  channels;
- deep look: channel means and spreads of the first three feature layers of
  a pretrained convolutional network (SqueezeNet 1.1, ImageNet). These are the
  statistics neural style transfer uses to describe style (Gatys et al. 2016;
  Huang and Belongie's AdaIN, 2017). They summarise colour, texture, grain and
  sharpness together while largely ignoring where things are in the frame,
  so they catch differences the hand-made measures miss.

Rendering in a style re-creates each of these on other footage: crop and
scale to the frame size, convert the frame rate, map lightness quantiles and
the colour cast and spread (a monotone curve on L* plus a Monge-Kantorovich
linear map on a*, b*), add the vignette, sharpen or soften and add or reduce
grain (calibrated on a short encoded sample so the result measures like the
style after compression), stabilise or add shake, match loudness and tonal
balance, and encode with the style's codec settings. The output is then
analysed like any upload and scored against the style.

Usage:
  recording_style.py learn VIDEO PROFILE.json
  recording_style.py apply VIDEO PROFILE.json OUTPUT.mp4 [--report REPORT.json]
  recording_style.py compare A.json B.json
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import av
import cv2
import numpy as np

if __package__:
    from .progress import Progress
else:
    from progress import Progress

VERSION = 1
SAMPLES = 48               # frames measured for colour, texture and vignette
MOTION_WIDTH = 640         # camera motion is measured on reduced frames
CUT_CORRELATION = .55
MATCH_THRESHOLD = 95.
LUMA = np.float32([.299, .587, .114])

# Group weights for the overall match. Editing pace is reported but not
# matched: it describes how footage was cut, not how it was recorded.
GROUP_WEIGHTS = {"format": 20, "color": 30, "texture": 20, "vignette": 5, "motion": 15, "audio": 10, "deep": 10}
# Early SqueezeNet 1.1 layers: conv1, fire2 and fire3 outputs.
DEEP_LAYERS = ("onnx_node!squeezenet0_relu0_fwd", "onnx_node!squeezenet0_concat0", "onnx_node!squeezenet0_concat1")
DEEP_FRAMES = 12
IMAGENET_MEAN, IMAGENET_STD = np.float32([.485, .456, .406]), np.float32([.229, .224, .225])


class DeepLook:
    """Style statistics from a pretrained CNN, run through OpenCV's DNN module.

    Frames are scaled to 448 px high and four 224 px crops are taken, so fine
    texture such as grain is seen near its recorded scale.
    """

    def __init__(self, model):
        self.net = cv2.dnn.readNetFromONNX(str(model))
        self.rows = []

    def add(self, rgb):
        height, width = rgb.shape[:2]
        scale = 448/height
        image = cv2.resize(rgb, (max(224, round(width*scale)), 448), interpolation=cv2.INTER_AREA)
        right = image.shape[1]
        for x, y in ((right//2-112, 0), (right//2-112, 224), (0, 112), (right-224, 112)):
            crop = (image[y:y+224, x:x+224].astype(np.float32)/255-IMAGENET_MEAN)/IMAGENET_STD
            self.net.setInput(cv2.dnn.blobFromImage(crop))
            outputs = self.net.forward(list(DEEP_LAYERS))
            self.rows.append(np.concatenate([np.r_[o[0].reshape(o.shape[1], -1).mean(axis=1),
                                                   o[0].reshape(o.shape[1], -1).std(axis=1)] for o in outputs]))

    def result(self):
        return [float(v) for v in np.mean(self.rows, axis=0)] if self.rows else None


def deep_distance(first, second):
    """Root mean square difference of log feature statistics."""
    a, b = np.asarray(first), np.asarray(second)
    return float(np.sqrt(np.mean((np.log(a+.05)-np.log(b+.05))**2)))


# ---------------------------------------------------------------- measuring

def lab(rgb):
    """uint8 RGB -> float32 CIELAB (L 0..100)."""
    return cv2.cvtColor(rgb.astype(np.float32)/255, cv2.COLOR_RGB2LAB)


def noise_sigma(channel, mask=None):
    """Immerkaer (1996) fast noise estimate on the flattest 60% of pixels."""
    channel = channel.astype(np.float32)
    kernel = np.float32([[1, -2, 1], [-2, 4, -2], [1, -2, 1]])
    response = np.abs(cv2.filter2D(channel, -1, kernel))[1:-1, 1:-1]
    gradient = cv2.magnitude(cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3),
                             cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3))[1:-1, 1:-1]
    flat = gradient <= np.percentile(gradient, 60)
    if mask is not None:
        flat &= mask[1:-1, 1:-1]
    if np.count_nonzero(flat) < 100:
        return 0.
    return float(math.sqrt(math.pi/2)/6*response[flat].mean())


def coarseness(channel):
    """Noise left after a 2x area reduction relative to full resolution.

    Independent pixel noise halves (0.5); grain spread over several pixels
    survives the reduction better (towards 1).
    """
    full = noise_sigma(channel)
    if full < .2:
        return .5
    half = cv2.resize(channel.astype(np.float32), (channel.shape[1]//2, channel.shape[0]//2), interpolation=cv2.INTER_AREA)
    return float(np.clip(noise_sigma(half)/full, .3, 1.2))


def sharpness(gray):
    """Fine-to-coarse gradient ratio on the strongest edges."""
    gray = gray.astype(np.float32)
    grad = lambda sigma: cv2.magnitude(*(cv2.Sobel(cv2.GaussianBlur(gray, (0, 0), sigma), cv2.CV_32F, dx, dy, ksize=3)
                                         for dx, dy in ((1, 0), (0, 1))))
    coarse = grad(2.)
    edges = coarse >= np.percentile(coarse, 98)
    if np.count_nonzero(edges) < 50 or coarse[edges].mean() < 2:
        return None
    return float(grad(.7)[edges].mean()/coarse[edges].mean())


def radius_squared(height, width, x=None, y=None):
    """Squared distance from the frame centre, 0 at the centre and 1 in the corners."""
    if x is None:
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    return (((x-(width-1)/2)/(width/2))**2+((y-(height-1)/2)/(height/2))**2)/2


def vignette_at(model, r2):
    """Lightness change (L* units) of a vignette model a*r^2 + b*r^4 at squared radius r2."""
    if model is None:
        return np.zeros_like(r2)
    return (model[0]*r2+model[1]*r2*r2).astype(np.float32)


class VignetteFit:
    """Least-squares radial falloff from scenery moving across the frame.

    When the camera moves, a point of scenery lands at a new distance from the
    centre. Its change in lightness then equals V(new) - V(old) for the falloff
    V, independent of what the scenery is. Flat, unclipped, well-registered
    pixels from many frame pairs give a linear system in V's two coefficients;
    each pair's mean is removed so exposure changes do not count.
    """

    def __init__(self):
        self.normal, self.target, self.count = np.zeros((2, 2)), np.zeros(2), 0

    def add(self, previous, current, matrix):
        height, width = current.shape
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        inverse = cv2.invertAffineTransform(matrix)
        px = inverse[0, 0]*x+inverse[0, 1]*y+inverse[0, 2]
        py = inverse[1, 0]*x+inverse[1, 1]*y+inverse[1, 2]
        before = cv2.remap(previous, px, py, cv2.INTER_LINEAR)
        gradient = cv2.magnitude(cv2.Sobel(current, cv2.CV_32F, 1, 0), cv2.Sobel(current, cv2.CV_32F, 0, 1))
        difference = current-before
        valid = ((px > 3) & (px < width-4) & (py > 3) & (py < height-4) & (current > 5) & (current < 95)
                 & (before > 5) & (before < 95) & (gradient < np.percentile(gradient, 50)) & (np.abs(difference) < 6))
        if np.count_nonzero(valid) < 500:
            return
        now, then = radius_squared(height, width)[valid], radius_squared(height, width, px, py)[valid]
        features = np.stack([now-then, now*now-then*then], axis=1).astype(np.float64)
        values = difference[valid].astype(np.float64)
        features -= features.mean(axis=0)
        values -= values.mean()
        self.normal += features.T @ features
        self.target += features.T @ values
        self.count += len(values)

    def result(self):
        if self.count < 20000 or np.linalg.cond(self.normal+np.eye(2)*1e-9) > 1e6 or \
                np.linalg.eigvalsh(self.normal).min() < 1:
            return None
        return [float(v) for v in np.linalg.solve(self.normal, self.target)]


def global_motion(previous, current):
    """Similarity transform (dx, dy in pixels, angle in radians, log scale) or None."""
    corners = cv2.goodFeaturesToTrack(previous, 400, .01, 8)
    if corners is None or len(corners) < 12:
        return None
    moved, good, _ = cv2.calcOpticalFlowPyrLK(previous, current, corners, None, winSize=(21, 21), maxLevel=3)
    keep = good[:, 0] > 0
    if np.count_nonzero(keep) < 10:
        return None
    matrix, inliers = cv2.estimateAffinePartial2D(corners[keep], moved[keep], method=cv2.RANSAC,
                                                  ransacReprojThreshold=1.5)
    if matrix is None or np.count_nonzero(inliers) < 8:
        return None
    scale = math.hypot(matrix[0, 0], matrix[1, 0])
    # Express the move as a rotation and scale about the frame centre plus a
    # shift, so roll does not leak into the measured shift.
    centre = np.array([previous.shape[1]/2, previous.shape[0]/2])
    shift = matrix[:, 2]+matrix[:, :2] @ centre-centre
    return float(shift[0]), float(shift[1]), math.atan2(matrix[1, 0], matrix[0, 0]), math.log(max(scale, 1e-6)), matrix


def histogram(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    return cv2.normalize(hist, hist).flatten()


def smooth(values, sigma):
    if len(values) < 3 or sigma <= 0:
        return np.array(values, np.float64)
    radius = int(3*sigma)+1
    kernel = np.exp(-.5*(np.arange(-radius, radius+1)/sigma)**2)
    kernel /= kernel.sum()
    # Odd reflection continues a trend past the ends, so a steady pan is not
    # mistaken for shake at the start and end of a clip.
    padded = np.pad(np.asarray(values, np.float64), radius, mode="reflect", reflect_type="odd") \
        if len(values) > radius else np.pad(np.asarray(values, np.float64), radius, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def trend(values, sigma):
    """Smooth camera path by Gaussian-weighted local quadratic regression.

    Unlike a plain blur, it follows steady pans and accelerating moves right
    up to the ends of a clip, so only real shake is left in the residual.
    """
    values = np.asarray(values, np.float64)
    count = len(values)
    if count < 4:
        return values.copy()
    radius = int(3*sigma)+1
    result = np.empty(count)
    for index in range(count):
        low, high = max(0, index-radius), min(count, index+radius+1)
        x = np.arange(low, high)-index
        weights = np.exp(-.5*(x/sigma)**2)
        design = np.stack([np.ones_like(x, dtype=np.float64), x, x*x], axis=1)
        if high-low < 4:
            design = design[:, :2]
        gram = design.T @ (design*weights[:, None])
        coefficients = np.linalg.lstsq(gram, design.T @ (weights*values[low:high]), rcond=None)[0]
        result[index] = coefficients[0]
    return result


def step_matrix(matrix, factor):
    """3x3 frame-to-frame transform measured on reduced frames, in full-size pixels."""
    step = np.eye(3)
    step[:2, :2] = matrix[:, :2]
    step[:2, 2] = matrix[:, 2]*factor
    return step


def parameters(matrices, centre):
    """(shift x, shift y, angle, log scale) of each 3x3 transform about the frame centre."""
    centre = np.asarray(centre, np.float64)
    rows = []
    for matrix in matrices:
        linear = matrix[:2, :2]
        shift = matrix[:2, 2]+linear @ centre-centre
        rows.append((shift[0], shift[1], math.atan2(linear[1, 0], linear[0, 0]),
                     math.log(max(math.hypot(linear[0, 0], linear[1, 0]), 1e-9))))
    rows = np.array(rows, np.float64).reshape(-1, 4)
    rows[:, 2] = np.unwrap(rows[:, 2])
    return rows


def compose(row, centre):
    """3x3 transform from (shift x, shift y, angle, log scale) about the centre."""
    centre = np.asarray(centre, np.float64)
    cos, sin, scale = math.cos(row[2]), math.sin(row[2]), math.exp(row[3])
    linear = scale*np.array([[cos, -sin], [sin, cos]])
    matrix = np.eye(3)
    matrix[:2, :2] = linear
    matrix[:2, 2] = np.asarray(row[:2])+centre-linear @ centre
    return matrix


def cumulative(steps):
    """Camera transforms of each frame relative to the first, composed exactly."""
    path, current = [np.eye(3)], np.eye(3)
    for step in steps:
        current = step @ current
        path.append(current)
    return path


def shake_measures(runs, fps, width, centre):
    """Shake and pan statistics from frame-to-frame 3x3 transforms within shots.

    runs: list of lists of 3x3 step matrices. Steps are composed exactly, so a
    pan combined with roll is not mistaken for shake.
    """
    residual, roll, pan, frequency_power = [], [], [], []
    for run in runs:
        if len(run) < 6:
            continue
        path = parameters(cumulative(run), centre)
        sigma = max(1., .5*fps)
        smooth_path = np.stack([trend(path[:, k], sigma) for k in range(4)], axis=1)
        shake = path-smooth_path
        residual.append(shake[:, :2]/width*100)
        roll.append(np.degrees(shake[:, 2]))
        pan.append(np.diff(smooth_path[:, :2], axis=0)/width*100*fps)
        velocity = np.diff(shake[:, :2], axis=0)
        if len(velocity) >= 8:
            power = np.abs(np.fft.rfft(velocity-velocity.mean(axis=0), axis=0))**2
            freqs = np.fft.rfftfreq(len(velocity), 1/fps)
            frequency_power.append((freqs, power.sum(axis=1)))
    if not residual:
        return {"shake": 0., "roll": 0., "frequency": 0., "pan": 0., "measured_frames": 0}
    residual = np.concatenate(residual)
    total_power = sum(p[1:].sum() for _, p in frequency_power)
    frequency = float(sum((f[1:]*p[1:]).sum() for f, p in frequency_power)/total_power) if total_power > 0 else 0.
    return {"shake": float(np.sqrt((residual**2).sum(axis=1).mean())),
            "roll": float(np.sqrt((np.concatenate(roll)**2).mean())),
            "frequency": frequency,
            "pan": float(np.sqrt((np.concatenate(pan)**2).sum(axis=1).mean())) if pan else 0.,
            "measured_frames": int(len(residual))}


def container_info(path):
    """Codec settings read from packets, without decoding."""
    info = {"video": None, "audio": None}
    with av.open(str(path)) as movie:
        video = next(iter(movie.streams.video), None)
        audio = next(iter(movie.streams.audio), None)
        if video is None:
            raise ValueError("The file has no video track.")
        streams = [s for s in (video, audio) if s is not None]
        sizes = {s.index: 0 for s in streams}
        keyframes, times, decode_order = [], [], []
        audio_end = 0.
        for packet in movie.demux(*streams):
            if packet.size == 0:
                continue
            sizes[packet.stream.index] += packet.size
            if packet.stream is video and packet.pts is not None:
                seconds = float(packet.pts*packet.time_base)
                times.append(seconds)
                decode_order.append(seconds)
                if packet.is_keyframe:
                    keyframes.append(seconds)
            elif packet.stream is audio and packet.pts is not None:
                audio_end = max(audio_end, float((packet.pts+(packet.duration or 0))*packet.time_base))
        context = video.codec_context
        times.sort()
        duration = (times[-1]-times[0])*len(times)/max(1, len(times)-1) if len(times) > 1 else 0.
        reordered = any(b < a for a, b in zip(decode_order, decode_order[1:]))
        gops = np.diff(keyframes) if len(keyframes) > 1 else np.array([duration or 1.])
        info["video"] = {
            "codec": context.name, "profile": context.profile, "pix_fmt": context.pix_fmt,
            "color_range": int(getattr(context, "color_range", 0) or 0),
            "colorspace": int(getattr(context, "colorspace", 2) or 2),
            "primaries": int(getattr(context, "color_primaries", 2) or 2),
            "transfer": int(getattr(context, "color_trc", 2) or 2),
            "frames": len(times), "duration": duration,
            "bitrate": 8*sizes[video.index]/duration if duration > 0 else 0.,
            "gop_seconds": float(np.median(gops)) if len(gops) else 0., "b_frames": bool(reordered),
        }
        if audio is not None:
            seconds = audio_end or duration
            info["audio"] = {"codec": audio.codec_context.name, "sample_rate": int(audio.codec_context.sample_rate),
                             "channels": int(audio.codec_context.layout.nb_channels),
                             "bitrate": 8*sizes[audio.index]/seconds if seconds > 0 else 0.}
    return info


def audio_measures(path):
    """Loudness, peak, noise floor and band balance of the mixed-down track."""
    with av.open(str(path)) as movie:
        stream = next(iter(movie.streams.audio), None)
        if stream is None:
            return None
        rate = int(stream.codec_context.sample_rate)
        resampler = av.AudioResampler(format="flt", layout="mono", rate=rate)
        chunks = []
        for frame in movie.decode(stream):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().reshape(-1))
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().reshape(-1))
    if not chunks:
        return None
    samples = np.concatenate(chunks).astype(np.float64)
    return signal_measures(samples, rate)


def signal_measures(samples, rate):
    from scipy.signal import welch

    block = max(1, int(.4*rate))
    count = len(samples)//block
    if count == 0:
        return None
    energy = (samples[:count*block].reshape(count, block)**2).mean(axis=1)
    levels = 10*np.log10(np.maximum(energy, 1e-12))
    gated = energy[levels > -70]
    loudness = 10*math.log10(max(gated.mean(), 1e-12)) if len(gated) else -120.
    freqs, power = welch(samples, rate, nperseg=min(4096, len(samples)))
    band = lambda low, high: 10*math.log10(max(power[(freqs >= low) & (freqs < high)].sum(), 1e-20))
    low, mid, high = band(20, 250), band(250, 4000), band(4000, rate/2+1)
    return {"loudness": float(loudness), "peak": float(20*math.log10(max(np.abs(samples).max(), 1e-9))),
            "noise_floor": float(np.percentile(levels, 10)), "low_mid": float(low-mid), "high_mid": float(high-mid)}


def analyse(path, progress=None, share=(0., 1.), encoding=None, style_model=None):
    """Measure a video's recording style. Returns a profile dict.

    Pixels come from path (an upright rendition). Codec settings and audio come
    from encoding when given, so a compatibility copy does not replace the
    original recording's settings.
    """
    report = progress or Progress()
    start, span = share
    encoding = encoding or path
    info = container_info(encoding)
    video = info["video"]
    with av.open(str(path)) as movie:
        total = max(1, movie.streams.video[0].frames or video["frames"])
    picks = set(np.linspace(0, total-1, min(SAMPLES, total)).round().astype(int).tolist())
    deep_picks = set(np.linspace(0, total-1, min(DEEP_FRAMES, total)).round().astype(int).tolist())
    deep = DeepLook(style_model) if style_model is not None else None
    L_hist = np.zeros(1001)
    chroma_hist = np.zeros(1001)
    ab_sum, ab_outer, ab_count = np.zeros(2), np.zeros((2, 2)), 0
    neutral = []
    vignette = VignetteFit()
    previous_L = None
    luma_noise, chroma_noise, grain, edges = [], [], [], []
    runs, current_run = [], []
    previous_small = previous_hist = None
    cuts = 0
    width = height = None
    times = []
    with av.open(str(path)) as movie:
        stream = movie.streams.video[0]
        stream.thread_type = "AUTO"
        for index, frame in enumerate(movie.decode(stream)):
            rgb = frame.to_ndarray(format="rgb24")
            height, width = rgb.shape[:2]
            if frame.pts is not None:
                times.append(float(frame.pts*frame.time_base))
            small = cv2.resize(rgb, (MOTION_WIDTH, max(2, round(height*MOTION_WIDTH/width))), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
            small_L = lab(small)[..., 0]
            hist = histogram(small)
            cut = previous_hist is not None and cv2.compareHist(previous_hist, hist, cv2.HISTCMP_CORREL) < CUT_CORRELATION
            if cut:
                cuts += 1
            if previous_small is not None and not cut:
                step = global_motion(previous_small, gray)
                if step is not None and math.hypot(step[0], step[1]) > 1.:
                    vignette.add(previous_L, small_L, step[4])
                if step is None:
                    if current_run:
                        runs.append(current_run)
                    current_run = []
                else:
                    current_run.append(step_matrix(step[4], width/MOTION_WIDTH))
            elif cut and current_run:
                runs.append(current_run)
                current_run = []
            previous_small, previous_hist, previous_L = gray, hist, small_L
            if deep is not None and index in deep_picks:
                deep.add(rgb)
            if index in picks:
                measured = lab(cv2.resize(rgb, (min(width, 640), max(2, round(height*min(width, 640)/width))),
                                          interpolation=cv2.INTER_AREA))
                L = measured[..., 0]
                L_hist += np.histogram(L, 1001, (0, 100.1))[0]
                ab = measured[..., 1:].reshape(-1, 2).astype(np.float64)
                ab_sum += ab.sum(axis=0)
                ab_outer += ab.T @ ab
                ab_count += len(ab)
                chroma = np.hypot(ab[:, 0], ab[:, 1])
                chroma_hist += np.histogram(chroma, 1001, (0, 150.15))[0]
                # The least colourful quarter of mid-tone pixels shows the grade's cast with
                # little influence from what was filmed.
                mids = (L.ravel() > 15) & (L.ravel() < 90)
                if np.count_nonzero(mids) > 100:
                    greys = mids & (chroma <= np.percentile(chroma[mids], 25))
                    neutral.append(np.median(ab[greys], axis=0))
                full = lab(rgb)
                luma = full[..., 0]*2.55
                luma_noise.append(noise_sigma(luma))
                chroma_noise.append((noise_sigma(full[..., 1])+noise_sigma(full[..., 2]))/2)
                grain.append(coarseness(luma))
                edge = sharpness(luma)
                if edge is not None:
                    edges.append(edge)
            report.update(1000*(start+span*.85*min(1, (index+1)/total)), 1000)
    if current_run:
        runs.append(current_run)
    if width is None:
        raise ValueError("The video has no decodable frames.")
    frames = len(times) or video["frames"]
    duration = (max(times)-min(times))*frames/max(1, frames-1) if len(times) > 1 else video["duration"]
    fps = frames/duration if duration > 0 else 30.
    quantile = lambda hist, edges_max: [float(v) for v in np.interp(
        np.linspace(0, 1, 101), np.cumsum(hist)/max(hist.sum(), 1), np.linspace(0, edges_max, len(hist)))]
    mean = ab_sum/max(ab_count, 1)
    covariance = ab_outer/max(ab_count, 1)-np.outer(mean, mean)
    motion = shake_measures(runs, fps, width, (width/2, height/2))
    audio = audio_measures(encoding) if info["audio"] is not None else None
    report.update(1000*(start+span), 1000)
    profile = {
        "version": VERSION,
        "format": {"width": width, "height": height, "fps": fps, "duration": duration, "frames": frames,
                   "bits_per_pixel": video["bitrate"]/max(1., width*height*fps),
                   **{key: video[key] for key in ("codec", "profile", "pix_fmt", "color_range", "colorspace",
                                                   "primaries", "transfer", "gop_seconds", "b_frames")}},
        "color": {"L_quantiles": quantile(L_hist, 100.1), "ab_mean": mean.tolist(),
                  "ab_covariance": covariance.tolist(), "chroma_quantiles": quantile(chroma_hist, 150.15),
                  "neutral_ab": (np.median(neutral, axis=0) if neutral else mean).tolist()},
        "texture": {"luma_noise": float(np.median(luma_noise)) if luma_noise else 0.,
                    "chroma_noise": float(np.median(chroma_noise)) if chroma_noise else 0.,
                    "grain_coarseness": float(np.median(grain)) if grain else .5,
                    "sharpness": float(np.median(edges)) if edges else None},
        "vignette": {"model": (model := vignette.result()), "corner": None if model is None else model[0]+model[1]},
        "motion": motion,
        "editing": {"cuts_per_minute": cuts/duration*60 if duration > 0 else 0.,
                    "mean_shot_seconds": duration/(cuts+1)},
        "audio": None if info["audio"] is None or audio is None else {**info["audio"], **audio},
        "deep": None if deep is None or deep.result() is None else {"model": "squeezenet1.1-7", "features": deep.result()},
    }
    profile["summary"] = describe(profile)
    return profile


# ---------------------------------------------------------------- comparing

def describe(profile):
    """A short human-readable summary of a style."""
    f, c, t, m = profile["format"], profile["color"], profile["texture"], profile["motion"]
    a, b = c["neutral_ab"]
    cast = "warm" if b > 6 else "cool" if b < -3 else "neutral"
    if a > 5:
        cast += ", magenta"
    elif a < -4:
        cast += ", green"
    L = c["L_quantiles"]
    contrast = L[95]-L[5]
    tone = "high contrast" if contrast > 75 else "flat" if contrast < 45 else "medium contrast"
    grain = "heavy grain" if t["luma_noise"] > 4 else "light grain" if t["luma_noise"] > 1.8 else "clean"
    camera = "handheld" if m["shake"] > .35 else "slight shake" if m["shake"] > .12 else "steady"
    parts = [f"{f['width']}×{f['height']}", f"{f['fps']:.3g} fps", f"{f['bits_per_pixel']*f['width']*f['height']*f['fps']/1e6:.1f} Mbps",
             cast, tone, grain, camera]
    if profile.get("audio"):
        parts.append(f"audio {profile['audio']['loudness']:.0f} dBFS")
    return " · ".join(parts)


def _gauss(difference, tolerance):
    return math.exp(-(difference/tolerance)**2)


def _log_ratio(a, b, offset=0.):
    return abs(math.log((max(a, 0)+offset+1e-9)/(max(b, 0)+offset+1e-9)))


def _mean(items):
    total = sum(weight for _, weight in items)
    return sum(score*weight for score, weight in items)/total if total else 1.


def similarity(first, second):
    """Percent match of two profiles (100 = same style) and per-group scores."""
    fa, fb = first["format"], second["format"]
    groups = {}
    groups["format"] = _mean([
        (_gauss(_log_ratio(fa["width"]/fa["height"], fb["width"]/fb["height"]), .05), 3),
        (_gauss(_log_ratio(fa["width"]*fa["height"], fb["width"]*fb["height"])/2, .3), 2),
        (_gauss(_log_ratio(fa["fps"], fb["fps"]), .08), 3),
        (_gauss(_log_ratio(fa["bits_per_pixel"], fb["bits_per_pixel"]), .6), 2),
        (_gauss(_log_ratio(fa["gop_seconds"], fb["gop_seconds"], .05), .7), 1),
        (1. if (fa["pix_fmt"], fa["color_range"]) == (fb["pix_fmt"], fb["color_range"]) else .5, 1),
        (1. if fa["codec"] == fb["codec"] else .5, 1),
    ])
    ca, cb = first["color"], second["color"]
    La, Lb = np.array(ca["L_quantiles"]), np.array(cb["L_quantiles"])
    # Black and white levels, contrast, the cast of near-neutral tones and
    # saturation describe a grade; mid-tone level and palette mostly describe
    # what was filmed, so they count less.
    groups["color"] = _mean([
        (_gauss(La[2]-Lb[2], 10), 1),
        (_gauss(La[98]-Lb[98], 10), 1),
        (_gauss((La[95]-La[5])-(Lb[95]-Lb[5]), 15), 2),
        (_gauss(La[50]-Lb[50], 15), 1),
        (_gauss(float(np.linalg.norm(np.subtract(ca["neutral_ab"], cb["neutral_ab"]))), 5), 3),
        (_gauss(_log_ratio(ca["chroma_quantiles"][75], cb["chroma_quantiles"][75], 2), .35), 2),
    ])
    ta, tb = first["texture"], second["texture"]
    texture = [(_gauss(_log_ratio(ta["luma_noise"], tb["luma_noise"], .3), .35), 2),
               (_gauss(_log_ratio(ta["chroma_noise"], tb["chroma_noise"], .3), .45), 1)]
    if min(ta["luma_noise"], tb["luma_noise"]) > .8:
        # Grain size only means something when there is visible grain.
        texture.append((_gauss(abs(ta["grain_coarseness"]-tb["grain_coarseness"]), .15), 1))
    if ta["sharpness"] is not None and tb["sharpness"] is not None:
        texture.append((_gauss(_log_ratio(ta["sharpness"], tb["sharpness"]), .2), 2))
    groups["texture"] = _mean(texture)
    va, vb = first["vignette"]["corner"], second["vignette"]["corner"]
    # A camera that never moved leaves the vignette unmeasured; it then does not count.
    groups["vignette"] = None if va is None or vb is None else _gauss(va-vb, 6)
    ma, mb = first["motion"], second["motion"]
    # Offsets set the smallest shake worth noticing: about 0.15% of the frame
    # width (one or two pixels) and 0.15 degrees of roll.
    motion = [(_gauss(_log_ratio(ma["shake"], mb["shake"], .15), .5), 2),
              (_gauss(_log_ratio(ma["roll"], mb["roll"], .15), .5), 1),
              (_gauss(_log_ratio(ma["pan"], mb["pan"], 1.), .8), 1)]
    if ma["shake"] > .3 and mb["shake"] > .3:
        motion.append((_gauss(_log_ratio(ma["frequency"], mb["frequency"], .5), .5), 1))
    groups["motion"] = _mean(motion)
    aa, ab = first.get("audio"), second.get("audio")
    if aa is None and ab is None:
        groups["audio"] = 1.
    elif aa is None or ab is None:
        groups["audio"] = 0.
    else:
        groups["audio"] = _mean([
            (_gauss(aa["loudness"]-ab["loudness"], 4), 2),
            (_gauss(aa["noise_floor"]-ab["noise_floor"], 6), 1),
            (_gauss(aa["low_mid"]-ab["low_mid"], 4), 1),
            (_gauss(aa["high_mid"]-ab["high_mid"], 4), 1),
            (1. if (aa["sample_rate"], aa["channels"]) == (ab["sample_rate"], ab["channels"]) else .6, 1),
        ])
    da, db = first.get("deep"), second.get("deep")
    groups["deep"] = _gauss(deep_distance(da["features"], db["features"]), .5) \
        if da and db and da["model"] == db["model"] else None
    used = [k for k in GROUP_WEIGHTS if groups[k] is not None]
    overall = sum(GROUP_WEIGHTS[k]*groups[k] for k in used)/sum(GROUP_WEIGHTS[k] for k in used)
    return round(100*overall, 2), {k: None if v is None else round(100*v, 1) for k, v in groups.items()}


def valid_profile(profile):
    """Structural check before a stored profile is trusted."""
    try:
        if profile["version"] != VERSION:
            return False
        f = profile["format"]
        numbers = [f["width"], f["height"], f["fps"], f["bits_per_pixel"], f["gop_seconds"],
                   *profile["color"]["L_quantiles"], *profile["color"]["ab_mean"],
                   *np.ravel(profile["color"]["ab_covariance"]), *profile["color"]["chroma_quantiles"],
                   *profile["color"]["neutral_ab"],
                   profile["texture"]["luma_noise"], profile["texture"]["chroma_noise"],
                   profile["texture"]["grain_coarseness"], *(profile["vignette"]["model"] or []),
                   profile["motion"]["shake"], profile["motion"]["roll"], profile["motion"]["pan"],
                   profile["motion"]["frequency"]]
        model = profile["vignette"]["model"]
        if len(profile["color"]["L_quantiles"]) != 101 or (model is not None and len(model) != 2):
            return False
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in numbers):
            return False
        if not (16 <= f["width"] <= 8192 and 16 <= f["height"] <= 8192 and 1 <= f["fps"] <= 240):
            return False
        deep = profile.get("deep")
        if deep is not None and (not isinstance(deep.get("model"), str) or not all(
                isinstance(v, (int, float)) and math.isfinite(v) for v in deep["features"])):
            return False
        audio = profile.get("audio")
        if audio is not None and not all(isinstance(audio[k], (int, float)) and math.isfinite(audio[k]) for k in
                                         ("loudness", "noise_floor", "low_mid", "high_mid", "sample_rate", "channels")):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------- rendering

def bounded_slope(curve, grid, overall, spread=2.5, anchor=None):
    """Limit a tone curve's local slope to within a factor of its overall slope.

    Quantile matching is steep wherever the source has few pixels (a small
    coloured detail on a flat background), which would blow those details out.
    A grade that is steep everywhere (a flat source to a contrasty style) keeps
    its overall slope. The curve is rebuilt from its clipped slope and shifted
    back so the anchor value (the median) still maps where the matching put it.
    """
    step = np.diff(grid)
    overall = float(np.clip(overall, .1, 10))
    slope = np.clip(np.diff(curve)/step, overall/spread, overall*spread)
    rebuilt = np.r_[0., np.cumsum(slope*step)]
    anchor = grid[len(grid)//2] if anchor is None else anchor
    rebuilt += np.interp(anchor, grid, curve)-np.interp(anchor, grid, rebuilt)
    return rebuilt


def lightness_curve(source, target):
    """Monotone L* lookup (1001 entries over 0..100) mapping source quantiles to target quantiles."""
    source, target = np.maximum.accumulate(np.array(source)), np.maximum.accumulate(np.array(target))
    source = source+np.arange(len(source))*1e-4
    grid = np.linspace(0, 100, 1001)
    curve = np.interp(grid, source, target)
    # Extend beyond the measured range with unit slope so highlights and shadows do not clip.
    curve = np.where(grid < source[0], target[0]+(grid-source[0]), curve)
    curve = np.where(grid > source[-1], target[-1]+(grid-source[-1]), curve)
    # Lightness keeps the full quantile match: black and white levels need
    # steep or flat ends. Only chroma (below) is slope-limited.
    return np.clip(smooth(curve, 4), 0, 100).astype(np.float32)


def _sqrtm(matrix):
    values, vectors = np.linalg.eigh(matrix)
    return vectors @ np.diag(np.sqrt(np.maximum(values, 1e-9))) @ vectors.T


def chroma_transform(source_mean, source_cov, target_mean, target_cov):
    """Monge-Kantorovich linear map (Pitie & Kokaram 2007) between a*, b* Gaussians."""
    cs, ct = np.array(source_cov)+np.eye(2)*1e-3, np.array(target_cov)+np.eye(2)*1e-3
    root = _sqrtm(cs)
    inverse = np.linalg.inv(root)
    matrix = inverse @ _sqrtm(root @ ct @ root) @ inverse
    return matrix.astype(np.float32), np.array(source_mean, np.float32), np.array(target_mean, np.float32)


def crop_to(width, height, aspect):
    """Centre crop (x, y, w, h) of a width x height frame with the given aspect."""
    if width/height > aspect:
        w = height*aspect
        return (width-w)/2, 0., w, float(height)
    h = width/aspect
    return 0., (height-h)/2, float(width), h


def style_shake(count, fps, width, motion, seed=0):
    """Band-limited shake (dx, dy, angle) with the style's amplitude and frequency.

    The band's centre is adjusted until the shake measures at the style's
    frequency with the same estimator used when learning.
    """
    wanted = np.zeros((count, 3))
    amplitude = motion["shake"]/100*width
    if amplitude <= .05 or count <= 4:
        return wanted
    target = min(max(motion["frequency"], .5), fps/3)
    noise = np.random.default_rng(seed).normal(0, 1, (count+64, 3))
    spectrum = np.fft.rfft(noise, axis=0)
    freqs = np.fft.rfftfreq(len(noise), 1/fps)
    sigma = max(1., .5*fps)
    centre = target
    for _ in range(5):
        band = np.exp(-.5*(np.log((freqs+1e-3)/centre)/.5)**2)
        shaped = np.fft.irfft(spectrum*band[:, None], n=len(noise), axis=0)[32:32+count]
        shaped -= np.stack([trend(shaped[:, k], sigma) for k in range(3)], axis=1)
        shaped /= np.maximum(shaped.std(axis=0), 1e-9)
        moves = np.diff(shaped[:, :2], axis=0)
        measured = shake_measures([[compose((dx, dy, 0., 0.), (0., 0.)) for dx, dy in moves]], fps, 100., (0., 0.))["frequency"]
        if measured <= 0 or abs(measured-target) < .05*target:
            break
        centre = float(np.clip(centre*target/measured, .2, fps/2.5))
    wanted[:, :2] = shaped[:, :2]*amplitude/math.sqrt(2)
    wanted[:, 2] = shaped[:, 2]*math.radians(motion["roll"])
    return wanted


def camera_corrections(steps, times, wanted_times, chosen, fps_source, fps, size, motion, seed=0, own=None):
    """Per output frame 3x3 transform that puts the chosen source frame on the styled camera path.

    steps[i] maps frame i-1 to frame i (identity at the first frame and at cuts).
    When the source already shakes in a similar way (own measures within a
    factor of two in amplitude and frequency), its own shake is kept and only
    rescaled, which preserves its natural character. Otherwise the shake is
    removed by following the smoothed path, evaluated at each output time so a
    frame-rate change does not add judder, and the style's shake is synthesised.
    """
    centre = (size[0]/2, size[1]/2)
    path = cumulative(steps[1:])
    rows = parameters(path, centre)
    light = np.stack([trend(rows[:, k], max(1., .5*fps_source)) for k in range(4)], axis=1)
    similar = (own is not None and motion["shake"] > .15 and own["shake"] > .15
               and .5 < motion["shake"]/own["shake"] < 2 and own["frequency"] > 0
               and .5 < motion["frequency"]/own["frequency"] < 2)
    if similar:
        # Keep the camera's own moves and shake; only rescale the shake.
        smooth_rows = rows.copy()
        residual = (rows-light)
        roll = np.clip(motion["roll"]/own["roll"], .25, 4) if own["roll"] > .05 else 1.
        smooth_rows[:, :2] += residual[:, :2]*(motion["shake"]/own["shake"]-1)
        smooth_rows[:, 2] += residual[:, 2]*(roll-1)
        shake = np.zeros((len(wanted_times), 3))
    else:
        # The new camera path is smoothed well beyond the 0.5 s scale that
        # defines shake when measuring, so measuring it again finds no leftover
        # shake. Where the heavy path departs a lot from the camera (a whip pan
        # or a fast deliberate move), the light path is followed instead, so
        # intentional moves are kept and borders stay inside the frame.
        heavy = np.stack([trend(rows[:, k], max(1., 1.25*fps_source)) for k in range(4)], axis=1)
        limit = np.array([.03*size[0], .03*size[0], math.radians(2.), .03])
        keep = np.exp(-((rows-heavy)/limit)**2)
        smooth_rows = light+(heavy-light)*keep
        shake = style_shake(len(wanted_times), fps, size[0], motion, seed)
    at = np.stack([np.interp(wanted_times, times, smooth_rows[:, k]) for k in range(4)], axis=1)
    if similar:
        # Follow the chosen frame's own (rescaled) position exactly.
        at = smooth_rows[chosen]
    result = []
    for j, frame in enumerate(chosen):
        desired = compose((at[j, 0]+shake[j, 0], at[j, 1]+shake[j, 1], at[j, 2]+shake[j, 2], at[j, 3]), centre)
        result.append(desired @ np.linalg.inv(path[frame]))
    return result


class Look:
    """Per-frame pixel pipeline: vignette, colour, sharpness and grain.

    The colour maps are fitted to frames already cropped and scaled to the
    output, with the vignette change applied first, so the lightness curve
    sees exactly the values it will be applied to.
    """

    def __init__(self, samples, target, size, source_vignette=None):
        width, height = size
        measured = [lab(frame) for frame in samples]
        radii = [radius_squared(*image.shape[:2]) for image in measured]
        chroma = np.concatenate([image[..., 1:].reshape(-1, 2) for image in measured]).astype(np.float64)
        self.matrix, self.source_mean, self.target_mean = chroma_transform(
            chroma.mean(axis=0), np.cov(chroma.T), target["color"]["ab_mean"], target["color"]["ab_covariance"])
        wanted = target["vignette"]["model"]
        own = source_vignette
        grid = np.linspace(0, 100, 1001)
        slope = 1.
        # Replace the source's falloff with the style's. The lightness curve
        # scales the falloff by its slope, so the change is divided by it.
        for _ in range(2):
            if wanted is None:
                model = [0., 0.]
            else:
                base = own or [0., 0.]
                model = [wanted[0]/slope-base[0], wanted[1]/slope-base[1]]
            self.vignette_change = lambda r2, model=model: vignette_at(model, r2)
            shifted = [image[..., 0]+self.vignette_change(r2) for image, r2 in zip(measured, radii)]
            values = np.concatenate([s.ravel() for s in shifted])
            self.curve = lightness_curve(np.percentile(values, np.linspace(0, 100, 101)), target["color"]["L_quantiles"])
            slope = float(np.clip(np.interp(values, grid, np.gradient(self.curve, grid)).mean(), .3, 3))
        self.vignette = self.vignette_change(radius_squared(height, width))
        # After the linear chroma map, a monotone curve on chroma magnitude
        # matches how saturation is distributed, not just its spread.
        mapped = (chroma-self.source_mean) @ self.matrix.T+self.target_mean
        magnitude = np.hypot(mapped[:, 0], mapped[:, 1])
        source_q = np.maximum.accumulate(np.percentile(magnitude, np.linspace(0, 100, 101)))+np.arange(101)*1e-4
        target_q = np.maximum.accumulate(np.array(target["color"]["chroma_quantiles"]))
        self.chroma_grid = np.linspace(0, 150, 1501)
        self.chroma_curve = smooth(np.interp(self.chroma_grid, source_q, target_q, right=None), 3)
        beyond = self.chroma_grid > source_q[-1]
        self.chroma_curve[beyond] = target_q[-1]+(self.chroma_grid[beyond]-source_q[-1])
        self.chroma_curve = bounded_slope(self.chroma_curve, self.chroma_grid,
                                          (target_q[90]+1)/(source_q[90]+1), 2., float(source_q[50]))
        self.chroma_curve = np.maximum.accumulate(np.maximum(self.chroma_curve, 0)).astype(np.float32)
        self.sharpen = 0.        # >0 unsharp amount, <0 blur sigma
        self.denoise = 0.        # bilateral strength in 8-bit levels
        self.grain = 0.          # luma grain sigma in 8-bit levels
        self.grain_size = 0.     # blur sigma applied to the grain
        self.chroma_grain = 0.
        self.rng = np.random.default_rng(1)

    def colour(self, rgb):
        image = lab(rgb)
        vignette = self.vignette if self.vignette.shape == image.shape[:2] else \
            self.vignette_change(radius_squared(*image.shape[:2]))
        L = image[..., 0]+vignette
        index = np.clip(L*10, 0, 1000)
        low = index.astype(np.int32)
        frac = index-low
        high = np.minimum(low+1, 1000)
        image[..., 0] = np.clip(self.curve[low]*(1-frac)+self.curve[high]*frac, 0, 100)
        ab = (image[..., 1:].reshape(-1, 2)-self.source_mean) @ self.matrix.T+self.target_mean
        magnitude = np.hypot(ab[:, 0], ab[:, 1])
        wanted = np.interp(magnitude, self.chroma_grid, self.chroma_curve)
        ab *= (wanted/np.maximum(magnitude, 1e-3))[:, None]
        image[..., 1:] = ab.reshape(image.shape[0], image.shape[1], 2)
        out = cv2.cvtColor(image, cv2.COLOR_LAB2RGB)
        return np.clip(out*255, 0, 255)

    def texture(self, rgb, seed=None):
        out = rgb.astype(np.float32)
        if self.sharpen < 0:
            out = cv2.GaussianBlur(out, (0, 0), -self.sharpen)
        elif self.sharpen > 0:
            out = out+self.sharpen*(out-cv2.GaussianBlur(out, (0, 0), 1.2))
        if self.denoise > 6:
            # Heavy grain needs non-local means; light noise a bilateral filter.
            out = cv2.fastNlMeansDenoisingColored(np.clip(np.rint(out), 0, 255).astype(np.uint8), None,
                                                  self.denoise/2, self.denoise/2, 5, 15).astype(np.float32)
        elif self.denoise > 0:
            # Edge-preserving, after sharpening, so sharpening does not bring the noise back.
            out = cv2.bilateralFilter(np.clip(out, 0, 255), 7, self.denoise*2.5, 2.)
        if self.grain > 0 or self.chroma_grain > 0:
            rng = np.random.default_rng(seed) if seed is not None else self.rng
            noise = rng.normal(0, 1, out.shape[:2]).astype(np.float32)
            if self.grain_size > 0:
                noise = cv2.GaussianBlur(noise, (0, 0), self.grain_size)
                noise /= max(float(noise.std()), 1e-6)
            out += (noise*self.grain)[..., None]
            if self.chroma_grain > 0:
                tint = rng.normal(0, 1, out.shape[:2]+(2,)).astype(np.float32)
                tint = cv2.GaussianBlur(tint, (0, 0), max(.8, self.grain_size))
                tint /= max(float(tint.std()), 1e-6)
                out[..., 0] += tint[..., 0]*self.chroma_grain
                out[..., 2] += tint[..., 1]*self.chroma_grain
        return np.clip(out, 0, 255)

    def __call__(self, rgb, seed=None):
        return np.rint(self.texture(self.colour(rgb), seed)).astype(np.uint8)


def grain_size_for(coarseness_target):
    """Blur sigma that gives white noise the requested coarseness, by simulation."""
    rng = np.random.default_rng(3)
    base = rng.normal(0, 1, (256, 256)).astype(np.float32)
    best, gap = 0., abs(coarseness(base*8+128)-coarseness_target)
    for sigma in np.arange(.3, 2.01, .1):
        noise = cv2.GaussianBlur(base, (0, 0), float(sigma))
        noise *= 8/max(float(noise.std()), 1e-6)
        value = abs(coarseness(noise+128)-coarseness_target)
        if value < gap:
            best, gap = float(sigma), value
    return best


def encoder_options(fmt, size, fps):
    width, height = size
    bitrate = int(min(max(fmt["bits_per_pixel"]*width*height*fps, 2e5), 2e8))
    gop = max(1, round(fmt["gop_seconds"]*fps)) if fmt["gop_seconds"] > 0 else max(1, round(2*fps))
    # A fixed keyframe interval like a camera's, without extra keyframes on busy frames.
    options = {"g": str(gop), "bf": "2" if fmt["b_frames"] else "0", "preset": "medium",
               "maxrate": str(int(bitrate*1.5)), "bufsize": str(int(bitrate*2)),
               "x264-params": f"keyint={gop}:min-keyint={gop}:scenecut=0"}
    profile = str(fmt.get("profile") or "").lower()
    for name in ("baseline", "main", "high"):
        if profile.startswith(name) or profile == "constrained baseline" and name == "baseline":
            options["profile"] = name
            break
    pix_fmt = "yuvj420p" if fmt["pix_fmt"] == "yuvj420p" else "yuv420p"
    return bitrate, options, pix_fmt


def encode_clip(frames, path, fmt, size, fps):
    bitrate, options, pix_fmt = encoder_options(fmt, size, fps)
    with av.open(str(path), "w") as movie:
        stream = movie.add_stream("libx264", rate=Fraction(fps).limit_denominator(1001), options=options)
        stream.width, stream.height = size
        stream.pix_fmt = pix_fmt
        stream.bit_rate = bitrate
        for frame in frames:
            for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)


def calibrate(look, samples, target, size, fps, directory):
    """Choose sharpening, denoising and grain so an encoded sample measures like the style."""
    texture = target["texture"]
    coloured = [look.colour(frame) for frame in samples]
    luma = lambda frame: lab(np.clip(frame, 0, 255).astype(np.uint8))[..., 0]*2.55
    # Sharpness first, on unencoded frames (strong edges barely respond to grain).
    if texture["sharpness"] is not None:
        def measured(amount):
            look.sharpen = amount
            values = [sharpness(luma(look.texture(frame, seed=0))) for frame in coloured[:4]]
            values = [v for v in values if v is not None]
            return float(np.median(values)) if values else None
        current = measured(0.)
        if current is not None:
            low, high = (-2.5, 0.) if current > texture["sharpness"] else (0., 3.)
            for _ in range(12):
                middle = (low+high)/2
                value = measured(middle)
                if value is None:
                    break
                if value > texture["sharpness"]:
                    high = middle
                else:
                    low = middle
            look.sharpen = (low+high)/2
    look.grain_size = grain_size_for(texture["grain_coarseness"])
    source_noise = float(np.median([noise_sigma(luma(look.texture(f, seed=0))) for f in coloured[:4]]))
    if source_noise > 1.3*texture["luma_noise"]+.3:
        look.denoise = source_noise
    look.grain = math.sqrt(max(texture["luma_noise"]**2-min(source_noise, texture["luma_noise"])**2, 0.))
    look.chroma_grain = texture["chroma_noise"]*.6 if texture["chroma_noise"] > 1 else 0.
    # Compression removes part of the grain; correct the amount on an encoded sample.
    for attempt in range(6):
        rendered = [np.rint(look.texture(frame, seed=index)).astype(np.uint8) for index, frame in enumerate(coloured)]
        clip = directory/f"calibrate-{attempt}.mp4"
        encode_clip(rendered, clip, target["format"], size, fps)
        with av.open(str(clip)) as movie:
            decoded = [frame.to_ndarray(format="rgb24") for frame in movie.decode(video=0)]
        clip.unlink()
        noise = float(np.median([noise_sigma(luma(frame)) for frame in decoded[len(decoded)//2:]]))
        if abs(noise-texture["luma_noise"]) < .06*texture["luma_noise"]+.05:
            break
        if noise < texture["luma_noise"]:
            look.grain = (look.grain or .5)*min(2.5, (texture["luma_noise"]+.2)/(noise+.2))
            look.denoise = max(0., look.denoise*.6)
        else:
            if look.grain > 0:
                look.grain *= max(.3, (texture["luma_noise"]+.2)/(noise+.2))
            else:
                look.denoise = max(look.denoise, 1.)*1.8


def render_audio(source, target, path):
    """Resample, rebalance and level the source track to the style; write AAC to path. Returns True if written."""
    style = target.get("audio")
    if style is None:
        return False
    with av.open(str(source)) as movie:
        stream = next(iter(movie.streams.audio), None)
        if stream is None:
            return False
        rate, channels = int(style["sample_rate"]), max(1, min(2, int(style["channels"])))
        layout = "stereo" if channels == 2 else "mono"
        resampler = av.AudioResampler(format="fltp", layout=layout, rate=rate)
        chunks = []
        for frame in movie.decode(stream):
            chunks.extend(f.to_ndarray() for f in resampler.resample(frame))
        chunks.extend(f.to_ndarray() for f in resampler.resample(None))
    if not chunks:
        return False
    samples = np.concatenate(chunks, axis=1).astype(np.float64)
    if signal_measures(samples.mean(axis=0), rate) is None:
        return False
    # Zero-phase equaliser: smooth shelves below 250 Hz and above 4 kHz, set in
    # two passes so the measured band balance lands on the style's.
    freqs = np.fft.rfftfreq(samples.shape[1], 1/rate)
    octave = np.log2(np.maximum(freqs, 1.)/1000)
    low_shelf = 1/(1+np.exp((octave-np.log2(.25))*4))
    high_shelf = 1/(1+np.exp(-(octave-np.log2(4))*4))
    spectrum = np.fft.rfft(samples, axis=1)
    low_db = high_db = 0.
    for _ in range(2):
        shaped = np.fft.irfft(spectrum*10**((low_db*low_shelf+high_db*high_shelf)/20), n=samples.shape[1], axis=1)
        now = signal_measures(shaped.mean(axis=0), rate)
        low_db = float(np.clip(low_db+style["low_mid"]-now["low_mid"], -24, 24))
        high_db = float(np.clip(high_db+style["high_mid"]-now["high_mid"], -24, 24))
    samples = np.fft.irfft(spectrum*10**((low_db*low_shelf+high_db*high_shelf)/20), n=samples.shape[1], axis=1)
    gain = lambda db: 10**(np.clip(db, -30, 30)/20)
    balanced = signal_measures(samples.mean(axis=0), rate)
    samples *= gain(style["loudness"]-balanced["loudness"])
    peak = np.abs(samples).max()
    if peak > .99:
        samples *= .99/peak
    samples = samples.astype(np.float32)
    bitrate = int(min(max(style.get("bitrate") or 128000, 32000), 512000))
    with av.open(str(path), "w", format="mp4") as movie:
        stream = movie.add_stream("aac", rate=rate)
        stream.layout = layout
        stream.bit_rate = bitrate
        step = 1024
        for offset in range(0, samples.shape[1], step):
            frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(samples[:, offset:offset+step]), format="fltp",
                                               layout=layout)
            frame.sample_rate = rate
            frame.pts = offset
            for packet in stream.encode(frame):
                movie.mux(packet)
        for packet in stream.encode():
            movie.mux(packet)
    return True


def source_motion(path):
    """Frame-to-frame 3x3 camera transforms of the source (identity where unknown or at cuts)."""
    steps = []
    previous = previous_hist = None
    with av.open(str(path)) as movie:
        stream = movie.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in movie.decode(stream):
            rgb = frame.to_ndarray(format="rgb24")
            height, width = rgb.shape[:2]
            small = cv2.resize(rgb, (MOTION_WIDTH, max(2, round(height*MOTION_WIDTH/width))), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
            hist = histogram(small)
            cut = previous_hist is not None and cv2.compareHist(previous_hist, hist, cv2.HISTCMP_CORREL) < CUT_CORRELATION
            step = None if previous is None or cut else global_motion(previous, gray)
            steps.append(np.eye(3) if step is None else step_matrix(step[4], width/MOTION_WIDTH))
            previous, previous_hist = gray, hist
    return steps


def apply(source, target, output, report_path=None, progress=None, style_model=None):
    """Render source in the target style, then measure the result against the style."""
    progress = progress or Progress()
    progress.update(0, 1000, label="Measuring the input footage", force=True)
    own = analyse(source, progress, (0., .25), style_model=style_model)
    fmt = target["format"]
    size = (int(fmt["width"])//2*2, int(fmt["height"])//2*2)
    fps = float(fmt["fps"])
    aspect = size[0]/size[1]
    with tempfile.TemporaryDirectory(dir=Path(output).parent) as scratch:
        work = Path(scratch)
        # Decode once to collect calibration samples and timing.
        with av.open(str(source)) as movie:
            stream = movie.streams.video[0]
            stream.thread_type = "AUTO"
            times, samples, spread = [], [], []
            total = own["format"]["frames"]
            middle = max(0, total//2-6)
            picks = set(np.linspace(0, max(0, total-1), min(32, max(1, total))).round().astype(int).tolist())
            for index, frame in enumerate(movie.decode(stream)):
                times.append(float(frame.pts*frame.time_base) if frame.pts is not None else index/own["format"]["fps"])
                if middle <= index < middle+12 or index in picks:
                    rgb = frame.to_ndarray(format="rgb24")
                    if middle <= index < middle+12:
                        samples.append(rgb)
                    if index in picks:
                        spread.append(rgb)
        source_size = (own["format"]["width"], own["format"]["height"])
        x, y, w, h = crop_to(*source_size, aspect)
        geometry = np.float32([[size[0]/w, 0, -x*size[0]/w], [0, size[1]/h, -y*size[1]/h]])
        warp = lambda rgb, matrix: cv2.warpAffine(rgb, matrix, size, flags=cv2.INTER_AREA if size[0] < w else cv2.INTER_CUBIC,
                                                  borderMode=cv2.BORDER_REFLECT)
        reduce = lambda rgb: cv2.resize(rgb, (min(size[0], 640), max(2, round(size[1]*min(size[0], 640)/size[0]))),
                                         interpolation=cv2.INTER_AREA)
        look = Look([reduce(warp(frame, geometry)) for frame in spread], target, size, own["vignette"]["model"])
        progress.update(260, 1000, label="Calibrating texture on an encoded sample", force=True)
        calibrate(look, [warp(s, geometry) for s in samples], target, size, fps, work)
        progress.update(300, 1000, label="Measuring camera motion", force=True)
        steps = source_motion(source)
        start = times[0] if times else 0.
        duration = (times[-1]-start)+(times[-1]-times[-2] if len(times) > 1 else 1/fps)
        count = max(1, int(round(duration*fps)))
        wanted = np.array([start+i/fps for i in range(count)])
        # The source frame shown at each output time (frame-rate conversion by nearest earlier frame).
        choose = np.clip(np.searchsorted(np.array(times), wanted+1e-6, side="right")-1, 0, len(times)-1)
        steps = (steps+[np.eye(3)]*len(times))[:len(times)]
        corrections = camera_corrections(steps, np.array(times), wanted, choose, own["format"]["fps"], fps,
                                         source_size, target["motion"], own=own["motion"])
        # Hide borders uncovered by the motion correction with a small zoom about the centre.
        corners = np.array([[x, y, 1.] for x in (0, source_size[0]) for y in (0, source_size[1])]).T
        reach = max((np.abs((matrix @ corners)[:2]-corners[:2]).max(axis=1)/np.array(source_size)).max()
                    for matrix in corrections) if corrections else 0.
        zoom = 1+min(.15, 2*reach)
        zoom_matrix = compose((0., 0., 0., math.log(zoom)), (source_size[0]/2, source_size[1]/2))
        video_path = work/"video.mp4"
        bitrate, options, pix_fmt = encoder_options(fmt, size, fps)
        written = 0
        with av.open(str(video_path), "w") as result, av.open(str(source)) as movie:
            stream = result.add_stream("libx264", rate=Fraction(fps).limit_denominator(1001), options=options)
            stream.width, stream.height = size
            stream.pix_fmt = pix_fmt
            stream.bit_rate = bitrate
            if fmt["color_range"] == 2:
                stream.codec_context.color_range = 2
            source_stream = movie.streams.video[0]
            source_stream.thread_type = "AUTO"
            position = 0
            for index, frame in enumerate(movie.decode(source_stream)):
                if position >= count:
                    break
                if choose[position] != index:
                    continue
                rgb = frame.to_ndarray(format="rgb24")
                while position < count and choose[position] == index:
                    full = np.vstack([geometry, [0, 0, 1]]) @ zoom_matrix @ corrections[position]
                    styled = look(warp(rgb, full[:2].astype(np.float32)), seed=1000+position)
                    for packet in stream.encode(av.VideoFrame.from_ndarray(styled, format="rgb24")):
                        result.mux(packet)
                    position += 1
                    written += 1
                progress.update(300+500*position/count, 1000, label=f"Rendering in style: frame {position} of {count}")
            for packet in stream.encode():
                result.mux(packet)
        audio_path = work/"audio.mp4"
        has_audio = render_audio(source, target, audio_path)
        Path(output).unlink(missing_ok=True)
        if has_audio:
            try:
                from .media import ffmpeg
            except ImportError:
                from media import ffmpeg
            ffmpeg("-v", "error", "-i", str(video_path), "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
                   "-c", "copy", "-shortest", "-movflags", "+faststart", str(output))
        else:
            video_path.replace(output)
    progress.update(800, 1000, label="Measuring the result against the style", force=True)
    measured = analyse(output, progress, (.8, .2), style_model=style_model)
    match, groups = similarity(target, measured)
    report = {"frames": written, "width": size[0], "height": size[1], "fps": fps, "audio": has_audio,
              "match": match, "groups": groups, "summary": measured["summary"],
              "settings": {"sharpen": round(look.sharpen, 3), "denoise": round(look.denoise, 2),
                           "grain": round(look.grain, 2), "grain_size": round(look.grain_size, 2),
                           "zoom": round(zoom, 3)}}
    if report_path is not None:
        Path(report_path).write_text(json.dumps(report))
    progress.finish()
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = cli.add_subparsers(dest="command", required=True)
    learn = commands.add_parser("learn")
    learn.add_argument("video", type=Path)
    learn.add_argument("profile", type=Path)
    learn.add_argument("--encoding-from", type=Path, help="Read codec settings and audio from this original file")
    render = commands.add_parser("apply")
    render.add_argument("video", type=Path)
    render.add_argument("profile", type=Path)
    render.add_argument("output", type=Path)
    render.add_argument("--report", type=Path)
    for command in (learn, render):
        command.add_argument("--style-model", type=Path, help="SqueezeNet 1.1 ONNX file for the deep look statistics")
    compare = commands.add_parser("compare")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)
    args = cli.parse_args()
    try:
        if args.command == "learn":
            profile = analyse(args.video, encoding=args.encoding_from, style_model=args.style_model)
            args.profile.write_text(json.dumps(profile))
            print(json.dumps({"summary": profile["summary"]}))
        elif args.command == "apply":
            profile = json.loads(args.profile.read_text())
            if not valid_profile(profile):
                raise ValueError("The style profile is damaged or from another version.")
            print(json.dumps(apply(args.video, profile, args.output, args.report, style_model=args.style_model)))
        else:
            first, second = (json.loads(path.read_text()) for path in (args.first, args.second))
            match, groups = similarity(first, second)
            print(json.dumps({"match": match, "groups": groups}))
    except (ValueError, OSError, av.FFmpegError) as error:
        cli.exit(1, f"{error}\n")


if __name__ == "__main__":
    sys.exit(main())
