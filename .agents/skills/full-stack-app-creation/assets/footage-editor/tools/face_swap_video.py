"""Render and verify a localized, lossless video face swap."""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from hashlib import sha256
from itertools import zip_longest
import json
import os
from pathlib import Path
from queue import Queue
import sys
from threading import Event, Thread, local

import av
import cv2
import numpy as np
from onnxruntime.capi.onnxruntime_pybind11_state import Fail, RuntimeException

from build_splats import TIME_SIGMA_FRAMES, advect
from face_fragments import FRAGMENTED, audio_sample_durations, fragment_audio, merge
from face_curvature import create_mesh_detector
from face_models import (ARCFACE_112, ARCFACE_128, FACE_LABELS, aligned_crop, detect_faces, encode, face_alpha,
                         gpu_available, landmark_alpha, occlusion, parse_face, read_photo, render, session)
from face_motion_blend import FaceBlend, soften_color_seam
from face_tracking import ActionTracker, face_from_points, mesh_five, motion_measures, smooth_track
from fetch_face_models import MODELS, file_hash
from media import encoder_threads, ffmpeg, restore_audio_timing
from progress import Progress, frame_total

# Progress units: tracking analysis, then rendering frames, then lossless
# verification and the playback rendition.
ANALYSE_SHARE, RENDER_SHARE, VERIFY_SHARE = .14, .86, .1
SHUTTER_CHOICES = (.25, .5, .75)


class FaceTrack:
    """Stabilize the captured projection using depth- and time-weighted landmark Gaussians."""

    def __init__(self, index, recognizer, identity=None, rivals=()):
        self.index = index
        self.recognizer = recognizer
        self.identity = identity
        self.rivals = rivals
        self.require_identity = identity is not None
        self.previous = None
        self.gray = None
        self.tracked = 0
        self.motion = 0.
        self.cut = True

    def update(self, image, faces):
        if not len(faces):
            self.gray = None
            return None
        previous = self.previous
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cut = self.gray is None or cv2.mean(cv2.absdiff(self.gray[::8, ::8], gray[::8, ::8]))[0] > 24
        if self.require_identity:
            best = self.match(image, faces, threshold=.48, margin=.05)
            if best is None and previous is not None and not cut:
                # Motion blur lowers the identity score. Accept a weaker match when the face is
                # where the tracked face just was, so a moving head stays swapped.
                best = self.match(image, faces, threshold=.25, margin=.05, near=previous)
            if best is None:
                self.gray = None
                return None
            face = faces[best].copy()
            return self.place(face, gray, cut)
        if previous is None:
            if self.index >= len(faces):
                return None
            face = faces[self.index].copy()
            self.identity = self.embedding(image, face)
        else:
            distance = np.linalg.norm(faces[:, :2] + faces[:, 2:4] / 2 - previous[:2] - previous[2:4] / 2, axis=1)
            best = int(np.argmin(distance))
            if len(faces) > 1 or cut or distance[best] > max(45, previous[2] * .85):
                best = self.match(image, faces, threshold=.42, margin=0)
                if best is None:
                    self.gray = None
                    return None
                if cut or distance[best] > max(45, previous[2] * .85):
                    cut = True
            face = faces[best].copy()
        return self.place(face, gray, cut)

    def place(self, face, gray, cut):
        self.cut = cut
        self.motion = 0.
        if self.previous is not None and not cut:
            delta = (face[4:14] - self.previous[4:14]).reshape(5,2)
            self.motion = float(np.percentile(np.linalg.norm(delta, axis=1), 75) / max(face[2], 1))
            if self.motion < .13:
                self.stabilize(face, gray)
        self.previous, self.gray = face, gray
        return face

    def match(self, image, faces, threshold, margin, near=None):
        if near is not None:
            center = near[:2] + near[2:4] / 2
            reach = max(45, near[2] * .85)
            faces = [face if np.linalg.norm(face[:2] + face[2:4] / 2 - center) <= reach else None for face in faces]
            if not any(face is not None for face in faces):
                return None
        candidates = [self.embedding(image, face) if face is not None else np.zeros_like(self.identity)
                      for face in faces]
        scores = [float(np.sum(candidate * self.identity)) for candidate in candidates]
        order = np.argsort(scores)
        best = int(order[-1])
        if scores[best] < threshold or (len(order) > 1 and scores[best] - scores[order[-2]] < margin):
            return None
        # Remember the other faces at selection time so a cut to one of them
        # does not become a match simply because they are now alone.
        if any(scores[best] - float(np.sum(candidates[best] * rival)) < margin for rival in self.rivals):
            return None
        return best

    def embedding(self, image, face):
        crop, _ = aligned_crop(image, face, ARCFACE_112, 112)
        return encode(self.recognizer, crop)

    def stabilize(self, face, gray):
        old = self.previous
        points = np.ascontiguousarray(old[4:14].reshape(5, 2))
        matte = np.full_like(gray, 255)
        indexes, projection = advect(self.gray, gray, points, matte)
        current = face[4:14].reshape(5, 2)
        sigma = max(1., face[2] * .025)
        shift = projection - current[indexes]
        distance_xy = current[:, None, :] - projection[None, :, :]
        # Treat inverse face-box scale as a depth cue. The nose splat sits in
        # front of the eye/mouth plane, so it does not pull those landmarks.
        depth = np.array([0., 0., .16, 0., 0.], np.float32)
        depth_shift = np.log(max(float(old[2]), 1.) / max(float(face[2]), 1.))
        distance_z = depth[:, None] - depth[indexes][None, :] + depth_shift
        # Depth is a relative scale cue in the captured view. A large residual
        # suppresses the previous observation at occlusions and rapid motion.
        # Let eye anchors respond more quickly than the cheeks and nose.
        spread = sigma * np.array([.58,.58,1,1,1])
        weight = np.exp(-.5 * (np.sum(distance_xy**2, axis=2)/spread[:,None]**2
                             + (distance_z/.12)**2 + (1/TIME_SIGMA_FRAMES)**2 + (self.motion/.07)**2))
        current += (weight @ shift) / (1 + weight.sum(axis=1, keepdims=True))
        self.tracked += int(np.count_nonzero(weight > .05))


def mask_from_labels(shape, crop, matrix, labels, refine=None, fallback=False, visible=None):
    try:
        base = face_alpha(labels, 20)
    except ValueError:
        # Video frames without a parsed face stay original; a single chosen image or frame
        # falls back to an oval from the landmarks so a selected face is always usable.
        if not fallback:
            raise
        base = landmark_alpha(crop.shape[0], 20)
    if visible is not None:
        # Hands, food and anything else in front of the face keep their own pixels.
        base = base*visible
    eyes = None
    if refine is not None:
        # Eyes and the mouth interior are kept from the frame itself.
        base, eyes = refine(crop, labels, base)
    inverse = cv2.invertAffineTransform(matrix)
    alpha = cv2.warpAffine(base, inverse, shape[1::-1])
    if eyes is not None and eyes.any():
        protected = cv2.warpAffine(eyes, inverse, shape[1::-1], flags=cv2.INTER_NEAREST)
        alpha[protected > 0] = 0
    return np.rint(alpha * 255).astype(np.uint8)


def mapped_face_mask(target, face, parser, refine=None, fallback=False):
    crop, matrix = aligned_crop(target, face, ARCFACE_128, 256)
    labels = parse_face(parser, crop)
    return crop, matrix, mask_from_labels(target.shape, crop, matrix, labels, refine, fallback)


def directional_sharpness(image, direction, mask):
    gray = cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return float(np.mean(np.abs(gx*direction[0]+gy*direction[1])[mask]))


def motion_kernel(vector, length):
    size = int(np.ceil(length)) | 1
    kernel = np.zeros((size, size), np.float32)
    direction = vector / max(1e-6, float(np.linalg.norm(vector)))
    center = (size-1)/2
    for t in np.linspace(-length/2, length/2, 4*size):
        x, y = center+t*direction
        kernel[int(round(y)), int(round(x))] += 1
    return kernel/kernel.sum()


def match_motion_blur(target, overlay, mask, velocity):
    """Blur the generated face along the head's motion as much as the camera did.

    The generator produces a sharp face even when the recorded face is smeared
    by fast motion, which reads as a pasted-on mask. The exposure is unknown,
    so several shutter fractions of the per-frame motion are tried and the one
    whose sharpness along the motion matches the recorded face is kept.
    """
    speed = float(np.linalg.norm(velocity))
    if speed < 3 or np.count_nonzero(mask) < 64:
        return overlay, 0.
    direction = velocity/speed
    wanted = directional_sharpness(target, direction, mask)
    best, best_gap, best_length = overlay, abs(directional_sharpness(overlay, direction, mask)-wanted), 0.
    for fraction in SHUTTER_CHOICES:
        length = speed*fraction
        if length < 1.5:
            continue
        blurred = cv2.filter2D(overlay, -1, motion_kernel(direction, length), borderType=cv2.BORDER_REPLICATE)
        gap = abs(directional_sharpness(blurred, direction, mask)-wanted)
        if gap < best_gap:
            best, best_gap, best_length = blurred, gap, length
    return best, best_length


def restore_detail(target, overlay, skin, scale):
    """Return camera-scale skin texture lost when a 256 px swap is enlarged.

    Only the parser's skin class carries the recorded high frequencies, so
    eyes, brows, nose and lips keep the generated identity.
    """
    if scale <= 1.2 or not skin.any():
        return overlay
    base = target.astype(np.float32)
    detail = base-cv2.GaussianBlur(base, (0, 0), .5*scale)
    amount = min(1., (scale-1)/1.5)
    return overlay+detail*(skin*amount)[..., None]


def blend_swap(target, matrix, alpha, swapped, soften=False, velocity=None, skin=None):
    """Blend a rendered 256px swap into the frame. Return the frame and the changed region, if any."""
    left, top, width, height = cv2.boundingRect(alpha)
    if not width or not height:
        return target, None
    transform = cv2.invertAffineTransform(matrix)
    transform[:, 2] -= [left, top]
    # Frame pixels per generated pixel. Enlarging uses cubic sampling.
    scale = float(abs(np.linalg.det(transform[:, :2])))**.5
    flags = cv2.INTER_CUBIC if scale > 1.05 else cv2.INTER_LINEAR
    overlay = cv2.warpAffine(swapped, transform, (width, height), flags=flags, borderMode=cv2.BORDER_REPLICATE)
    roi = np.s_[top:top+height, left:left+width]
    weight = alpha[roi][..., None].astype(np.float32) / 255
    if skin is not None:
        skin_frame = cv2.warpAffine(skin, transform, (width, height), flags=cv2.INTER_LINEAR)
        overlay = restore_detail(target[roi], overlay, skin_frame, scale)
    if velocity is not None:
        overlay, _ = match_motion_blur(target[roi], overlay, weight[..., 0] > .5, np.asarray(velocity, np.float32))
    overlay = np.clip(overlay, 0, 255)
    if soften:
        overlay = soften_color_seam(target[roi], overlay, weight[...,0])
    result = target.copy()
    result[roi] = np.rint(target[roi] + (overlay-target[roi])*weight).astype(np.uint8)
    return result, roi


def composite(target, face, swapper, identity, parser, refine=None):
    crop, matrix, alpha = mapped_face_mask(target, face, parser, refine)
    if not cv2.boundingRect(alpha)[2]:
        return target, alpha
    return blend_swap(target, matrix, alpha, render(swapper, crop, identity), refine is not None)[0], alpha


def video_signature(path, progress=None):
    with av.open(str(path)) as movie:
        stream = movie.streams.video[0]
        stream.codec_context.thread_type = "AUTO"
        stream.codec_context.thread_count = 0
        signature = []
        for frame in movie.decode(stream):
            signature.append((frame.pts*frame.time_base, frame.duration*frame.time_base,
                              sha256(frame.to_ndarray(format="bgr24")).digest()))
            if progress is not None:
                progress(len(signature))
        return signature


def same_frame(actual, expected, last):
    """Compare a decoded output frame with the composite that was encoded.

    MP4 stores each sample's duration as the gap to the next decode timestamp, so only the
    final frame keeps the duration written for it. Some recordings declare frame durations
    that disagree with their own timestamps (for example 40 ticks between frames 400 apart);
    for those, the timestamps and pixels are what can be preserved exactly.
    """
    (time, duration, digest), (expected_time, expected_duration, expected_digest) = actual, expected
    return time == expected_time and digest == expected_digest and (not last or duration == expected_duration)


def make_preview(source, output, progress=None):
    with av.open(str(source)) as movie:
        video = movie.streams.video[0]
        total = frame_total(video)
        scale = min(1, 960 / max(video.width, video.height))
        width, height = [max(2, round(side * scale / 2) * 2) for side in (video.width, video.height)]
    # The verified RGB export stays untouched. This smaller H.264 rendition
    # has shorter keyframe intervals for playback and scrubbing in the editor.
    ffmpeg("-loglevel", "error", "-copyts", "-i", source, "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", f"scale={width}:{height}:out_color_matrix=bt709,setsar=1",
           "-c:v", "libx264", "-preset", "veryfast", "-threads:v", str(encoder_threads()), "-crf", "19", "-g", "36",
           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "iec61966-2-1", "-fps_mode", "passthrough", "-c:a", "aac",
           "-b:a", "128k", "-avoid_negative_ts", "disabled", "-movflags", "+faststart", output,
           progress=None if progress is None else lambda frames: progress(frames, total))


def audio_signature(path, include_duration=True):
    packets, decoded = sha256(), sha256()
    with av.open(str(path)) as movie:
        if not movie.streams.audio:
            return None
        stream = movie.streams.audio[0]
        packets.update(stream.codec_context.extradata or b"")
        for packet in movie.demux(stream):
            if packet.size:
                timing = packet.pts*packet.time_base, packet.dts*packet.time_base
                if include_duration:
                    timing += (packet.duration*packet.time_base,)
                packets.update(repr((*timing, packet.size)).encode())
                packets.update(bytes(packet))
    with av.open(str(path)) as movie:
        for frame in movie.decode(audio=0):
            decoded.update(repr((frame.pts*frame.time_base, frame.samples)).encode())
            decoded.update(frame.to_ndarray().tobytes())
    return packets.digest(), decoded.digest()


def selected_identity(target, selection, detector, recognizer):
    time, x, y = selection
    last = None
    with av.open(str(target), format="mp4") as movie:
        if len(movie.streams.video) != 1:
            raise ValueError("Choose an MP4 with one video track.")
        stream = movie.streams.video[0]
        if stream.duration is not None and time > float(stream.duration * stream.time_base) + 1:
            raise ValueError("The selected time is outside the target video.")
        timestamp = time + (movie.start_time or 0) / av.time_base
        movie.seek(int(timestamp / stream.time_base), stream=stream, backward=True)
        for frame in movie.decode(stream):
            if frame.pts is None:
                continue
            if float(frame.pts * frame.time_base) > timestamp + .0001 and last is not None:
                break
            last = frame
            if float(frame.pts * frame.time_base) >= timestamp - .0001:
                break
        if last is None:
            raise ValueError("This target frame could not be read. Select a frame again.")
        image = last.to_ndarray(format="bgr24")
    # A user-selected frame gets the thorough search, so a tilted or blurred face can be chosen.
    faces = detect_faces(image, detector, thorough=True)
    face = face_at_point(image, (x, y), detector, faces)
    crop, _ = aligned_crop(image, face, ARCFACE_112, 112)
    rivals = tuple(encode(recognizer, aligned_crop(image, candidate, ARCFACE_112, 112)[0])
                   for candidate in faces if not np.array_equal(candidate, face))
    return encode(recognizer, crop), rivals


def _face_near(point, faces, reach):
    """Return the face whose center is closest to the point, in face-size units, within reach."""
    best = None
    for face in faces:
        distance = float(np.linalg.norm((point - face[:2] - face[2:4] / 2) / np.maximum(face[2:4], 1)))
        if distance <= reach and (best is None or distance < best[0]):
            best = distance, face
    return None if best is None else best[1]


def _faces_around(image, point, detector):
    """Search a window around a click, enlarged, for small, tilted or blurred faces."""
    height, width = image.shape[:2]
    side = int(max(160, .4 * min(height, width)))
    left = int(np.clip(point[0] - side / 2, 0, max(0, width - side)))
    top = int(np.clip(point[1] - side / 2, 0, max(0, height - side)))
    window = image[top:top + side, left:left + side]
    scale = max(1., 640 / max(window.shape[:2]))
    enlarged = cv2.resize(window, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale > 1 else window
    faces = detect_faces(enlarged, detector, thorough=True, min_score=.35)
    if not len(faces):
        return []
    faces = np.array(faces, np.float32)
    faces[:, :14] /= scale
    faces[:, 0:14:2] += left
    faces[:, 1:14:2] += top
    return faces


def face_at_point(image, coordinates, detector, faces=None):
    """Find the face the user clicked.

    Clicks inside or next to a face pick the nearest one. If none is close, a focused search
    around the click (enlarged, rotated, lower score) recovers small, tilted or blurred faces.
    """
    if faces is None:
        faces = detect_faces(image, detector, thorough=True)
    x, y = coordinates
    point = np.array([x * image.shape[1], y * image.shape[0]], np.float32)
    face = _face_near(point, faces, 1.)
    if face is None:
        nearby = _faces_around(image, point, detector)
        face = _face_near(point, nearby, 1.) if len(nearby) else None
        if face is None:
            # Still accept a click that lands a little outside the face, for example on hair.
            combined = [*faces, *nearby]
            face = _face_near(point, combined, 2.5)
    if face is None:
        raise ValueError("No face was found near the selected point. Click on a face, or zoom in on a small one.")
    return face


def verified_models(models):
    # Hash the model files concurrently. hashlib releases the GIL for large blocks.
    with ThreadPoolExecutor(len(MODELS)) as pool:
        checks = {name: pool.submit(lambda path, digest: path.is_file() and file_hash(path) == digest,
                                    models / name, digest)
                  for name, (_, digest) in MODELS.items()}
        for name, check in checks.items():
            if not check.result():
                raise ValueError(f"Missing or unverified model: {name}. See Face Swap setup.")


def inference_workers():
    # The swapper is memory-bound and stops scaling past a few threads per call, so frames
    # are rendered concurrently instead. Two threads per call leaves room for detection.
    return max(1, min(3, (os.cpu_count() or 2) // 4))


class FrameReader(Thread):
    """Demux and decode ahead of the renderer, detecting faces on a small pool, preserving order.

    Once the swap runs on the GPU, face detection is the slowest CPU step, so frames are
    detected concurrently. Each detection thread owns its detector; YuNet is not thread-safe.
    """

    def __init__(self, container, video, audio, detector_model, depth=16, detectors=3, detect=True):
        super().__init__(daemon=True)
        self.detecting = detect
        self.container, self.video, self.audio = container, video, audio
        self.detector_model = detector_model
        self.local = local()
        self.pool = ThreadPoolExecutor(detectors)
        self.items = Queue(depth)
        self.stopped = Event()

    def detect(self, image):
        detector = getattr(self.local, "detector", None)
        if detector is None:
            detector = self.local.detector = cv2.FaceDetectorYN.create(str(self.detector_model), "", (320,320), .78)
        return detect_faces(image, detector)

    def run(self):
        try:
            for packet in self.container.demux(self.video, *([self.audio] if self.audio is not None else [])):
                if self.stopped.is_set():
                    return
                if packet.stream.type == "audio":
                    self.items.put(("audio", packet))
                    continue
                for frame in packet.decode():
                    image = frame.to_ndarray(format="bgr24")
                    job = self.pool.submit(self.detect, image) if self.detecting else None
                    self.items.put(("video", frame, image, job))
            self.items.put(("end",))
        except BaseException as error:
            self.items.put(("error", error))

    def __iter__(self):
        while True:
            item = self.items.get()
            if item[0] == "end":
                return
            if item[0] == "error":
                raise item[1]
            yield item

    def close(self):
        self.stopped.set()
        # Drain so a reader blocked on a full queue can observe the stop flag.
        while self.is_alive():
            while not self.items.empty():
                self.items.get_nowait()
            self.join(.05)
        self.pool.shutdown(cancel_futures=True)


def covered_share(labels, visible):
    """Share of the parsed face hidden behind something, for the report."""
    # The occlusion weight is conservative at the face outline, so only the
    # inner face counts.
    face = cv2.erode(np.isin(labels, FACE_LABELS).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    return float(np.mean(visible[face] < .5)) if face.any() else 0.


def skin_weight(labels):
    """Soft skin-class weight in crop space, kept away from feature edges."""
    skin = cv2.erode((labels == 1).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    return cv2.GaussianBlur(skin, (0, 0), 2)


def analyse(target, models, recognizer, mesh, identity, rivals, target_index, progress, occluder=None):
    """First pass: follow the face through every frame, then smooth the track."""
    records = []
    with av.open(str(target), format="mp4") as movie:
        video = movie.streams.video[0]
        video.thread_count = 3
        total = frame_total(video)
        fps = float(video.average_rate or 30)
        reader = FrameReader(movie, video, None, models / "face_detection_yunet_2023mar.onnx")
        reader.start()
        try:
            tracker = ActionTracker(recognizer, mesh, identity, rivals, target_index, occluder)
            for _, _, image, detection in reader:
                records.append(tracker.step(image, detection.result()))
                progress.update(ANALYSE_SHARE * 1000 * min(1, len(records) / max(total, 1)),
                                label=f"Tracking the face: frame {len(records)} of {max(total, len(records))}")
        finally:
            reader.close()
    track = smooth_track(records, fps)
    plan = []
    for (points, bridged), (motion, velocity), record in zip(track, motion_measures(track), records):
        if points is None:
            plan.append(None)
        else:
            plan.append((face_from_points(points), motion, record["cut"], velocity))
    stats = dict(tracker.stats, bridged=sum(flag for _, flag in track))
    return plan, stats


def run(source, target, output, models, source_index=0, target_index=0, target_point=None, mesh_model=None):
    cv2.setNumThreads(2)
    progress = Progress(1000, path=output / "progress")
    progress.update(0, label="Loading Face Swap models", force=True)
    workers = inference_workers()
    with ThreadPoolExecutor(4) as loader:
        # ONNX Runtime optimizes each graph on load. Building the sessions together saves several seconds.
        sessions = [loader.submit(session, models / name, threads) for name, threads in
                    (("arcface_w600k_r50.onnx", 4), ("hyperswap_1a_256.onnx", 2), ("bisenet_resnet_18.onnx", 2),
                     ("xseg_1.onnx", 2))]
        verified_models(models)
        recognizer, swapper, parser, occluder = (job.result() for job in sessions)
    detector = cv2.FaceDetectorYN.create(str(models / "face_detection_yunet_2023mar.onnx"), "", (320,320), .78)
    actor, _ = read_photo(source)
    faces = detect_faces(actor, detector)
    if not 0 <= source_index < len(faces):
        raise ValueError(f"Source face index is unavailable ({len(faces)} faces detected).")
    crop, _ = aligned_crop(actor, faces[source_index], ARCFACE_112, 112)
    identity = encode(recognizer, crop)
    locked_identity, rivals = selected_identity(target, target_point, detector, recognizer) if target_point is not None else (None, ())
    hashes = []
    changed_frames = occluded_frames = 0
    pending = output / "pending.mp4"
    # The reader thread uses the container, so release the pipeline before the container closes.
    with av.open(str(target), format="mp4") as original, ExitStack() as resources:
        mesh = resources.enter_context(create_mesh_detector(mesh_model)) if mesh_model is not None else None
        tracking_mesh = resources.enter_context(create_mesh_detector(mesh_model)) if mesh_model is not None else None
        plan, tracking = analyse(target, models, recognizer, tracking_mesh, locked_identity, rivals, target_index, progress,
                                 occluder)
        blend = FaceBlend(mesh)
        pool = resources.enter_context(ThreadPoolExecutor(workers * 2))

        if len(original.streams.video) != 1 or len(original.streams.audio) > 1 or len(original.streams) > 2:
            raise ValueError("Choose an MP4 with one video track and at most one audio track.")
        video = original.streams.video[0]
        audio = next(iter(original.streams.audio), None)
        if audio is not None and audio.codec_context.name != "aac":
            raise ValueError("Face Swap supports AAC audio in MP4.")
        video.thread_count = 3
        total = frame_total(video)
        separate_audio = audio is not None and video.frames == 0
        video_clock = video.time_base.denominator
        audio_clock = audio.time_base.denominator if audio is not None else None
        track_output = output / "video-only.mp4" if separate_audio else pending
        options = {"movflags":FRAGMENTED if separate_audio else "+faststart",
                   "video_track_timescale":str(video_clock), "movie_timescale":str(video_clock)}
        with av.open(str(track_output), mode="w", options=options) as result:
            stream = result.add_stream("libx264rgb", rate=video.average_rate or 30,
                                       options={"crf":"0","preset":"ultrafast","tune":"zerolatency","g":"48"})
            stream.width, stream.height = video.width, video.height
            stream.pix_fmt = "bgr24"
            # Signal full-range RGB explicitly. Without it Chrome can display
            # a byte-verifiable H.264 RGB track through a YUV color matrix.
            stream.codec_context.colorspace = 0
            stream.codec_context.color_range = 2
            stream.codec_context.color_primaries = 1
            stream.codec_context.color_trc = 13
            stream.time_base = stream.codec_context.time_base = video.time_base
            stream.thread_count = 4
            audio_out = result.add_stream_from_template(audio) if audio is not None and not separate_audio else None
            reader = FrameReader(original, video, audio if audio_out is not None else None,
                                 models / "face_detection_yunet_2023mar.onnx", detect=False)
            resources.callback(reader.close)
            reader.start()
            # Frames move through three stages: tracking (in order), inference on the pool
            # (out of order), then masking, blending and encoding (in order). Tracking never
            # depends on a rendered result, so it can run several frames ahead.
            window = deque()

            def finish(entry):
                nonlocal changed_frames, occluded_frames, queued
                if entry[0] == "audio":
                    # Audio keeps its original place relative to the frames demuxed before it.
                    if entry[1].size:
                        entry[1].stream = audio_out
                        result.mux(entry[1])
                    return
                queued -= 1
                _, frame, image, job = entry
                edited = image
                if job is None:
                    blend.reset()
                else:
                    crop, matrix, motion, cut, velocity, labels, swapped, uncovered = job
                    try:
                        parsed, visible = labels.result(), uncovered.result()
                        occluded_frames += int(covered_share(parsed, visible) > .02)
                        alpha = mask_from_labels(image.shape, crop, matrix, parsed,
                                                 lambda crop, labels, alpha: blend.refine(crop, labels, alpha, motion, cut),
                                                 visible=visible)
                        edited, roi = blend_swap(image, matrix, alpha, swapped.result(), True, velocity, skin_weight(parsed))
                    except ValueError:
                        blend.reset()
                        edited, roi = image, None
                    if roi is not None:
                        # Everything outside the bounding box is a copy, so only the box can differ.
                        delta = np.any(edited[roi] != image[roi], axis=2)
                        if np.any(delta & (alpha[roi] == 0)):
                            raise ValueError("Pixels outside the face mask changed.")
                        changed_frames += int(delta.any())
                timed = av.VideoFrame.from_ndarray(edited, format="bgr24")
                timed.pts, timed.time_base = frame.pts, frame.time_base
                # Assign the original duration to each packet, including the final frame.
                for encoded in stream.encode(timed):
                    if separate_audio:
                        encoded.dts -= video.start_time or 0
                    encoded.duration = frame.duration
                    result.mux(encoded)
                hashes.append((frame.pts*frame.time_base, frame.duration*frame.time_base, sha256(edited).digest()))
                progress.update(1000 * (ANALYSE_SHARE + (RENDER_SHARE - ANALYSE_SHARE) * min(1, len(hashes) / max(total, 1))),
                                label=f"Swapping faces: frame {len(hashes)} of {max(total, len(hashes))}")

            queued = 0
            frame_index = 0
            for item in reader:
                if item[0] == "audio":
                    window.append(item)
                    continue
                _, frame, image, _ = item
                if frame.rotation or frame.width != stream.width or frame.height != stream.height:
                    raise ValueError("Face Swap requires fixed frame dimensions and baked-in orientation.")
                if frame_index >= len(plan):
                    raise ValueError("The target changed between tracking and rendering.")
                step = plan[frame_index]
                frame_index += 1
                job = None
                if step is not None:
                    face, motion, cut, velocity = step
                    try:
                        crop, matrix = aligned_crop(image, face, ARCFACE_128, 256)
                        job = (crop, matrix, motion, cut, velocity, pool.submit(parse_face, parser, crop),
                               pool.submit(render, swapper, crop, identity), pool.submit(occlusion, occluder, crop))
                    except ValueError:
                        job = None
                window.append(("video", frame, image, job))
                queued += 1
                while queued > workers + 1:
                    finish(window.popleft())
            while window:
                finish(window.popleft())
            for packet in stream.encode():
                result.mux(packet)
    verify_label = "Verifying the lossless export"
    progress.update(RENDER_SHARE * 1000, label=verify_label)
    if separate_audio:
        audio_path = output / "audio-only.mp4"
        durations = audio_sample_durations(target)
        fragment_audio(target, audio_path, durations, video_clock)
        if (durations != audio_sample_durations(audio_path)
                or audio_signature(target, False) != audio_signature(audio_path, False)):
            raise ValueError("Independent AAC fragments changed packet bytes or timing.")
        # The merge copies entire audio sample tables and bytes from the verified
        # audio-only track. Multi-track demux can infer a different first packet
        # duration, so verify the merged payload/clock and decoded samples separately.
        merge(track_output, audio_path, pending, video_clock, audio_clock)
        if durations != audio_sample_durations(pending):
            raise ValueError("Stored AAC sample durations changed in the merged file.")
        track_output.unlink()
        audio_path.unlink()
    if not changed_frames:
        raise ValueError("No target face could be swapped. Check the face index and visibility.")
    original_audio = audio_signature(target, include_duration=not separate_audio)
    if not separate_audio and original_audio != audio_signature(pending) and original_audio is not None:
        restore_audio_timing(target, pending)
    if original_audio != audio_signature(pending, include_duration=not separate_audio):
        raise ValueError("Audio packets or decoded audio timing changed.")
    checked = lambda count: progress.update(1000 * (RENDER_SHARE + VERIFY_SHARE * min(1, count / len(hashes))))
    for index, (actual, expected) in enumerate(zip_longest(video_signature(pending, checked), hashes)):
        if actual is None or expected is None or not same_frame(actual, expected, index == len(hashes) - 1):
            raise ValueError(f"Lossless video verification failed at frame {index+1}.")
    pending.replace(output / "face-swap.mp4")
    report = {"frames":len(hashes), "swapped":changed_frames, "unchanged":len(hashes)-changed_frames,
              "tracking": tracking, "video": "verified", "audio": "verified",
              "outside_mask": "byte exact", "eye_detail_frames":blend.eyes,
              "mouth_detail_frames":blend.mouths, "tongue_frames":blend.tongues, "occluded_frames":occluded_frames,
              "seam_stabilized_frames":blend.steadied, "rapid_motion_resets":blend.rapid}
    (output / "verification.json").write_text(json.dumps(report))
    progress.update(1000 * (RENDER_SHARE + VERIFY_SHARE), label="Preparing smooth playback", force=True)
    return report


def run_image(source, target, output, models, source_index=0, target_point=None, mesh_model=None):
    """Swap one face in a still image and write a verified lossless PNG."""
    from PIL import Image

    cv2.setNumThreads(2)
    progress = Progress(1000, path=output / "progress")
    progress.update(0, label="Loading Face Swap models", force=True)
    with ThreadPoolExecutor(4) as loader:
        sessions = [loader.submit(session, models / name, threads) for name, threads in
                    (("arcface_w600k_r50.onnx", 4), ("hyperswap_1a_256.onnx", 4), ("bisenet_resnet_18.onnx", 4),
                     ("xseg_1.onnx", 2))]
        verified_models(models)
        recognizer, swapper, parser, occluder = (job.result() for job in sessions)
    detector = cv2.FaceDetectorYN.create(str(models / "face_detection_yunet_2023mar.onnx"), "", (320,320), .78)
    actor, _ = read_photo(source)
    faces = detect_faces(actor, detector, thorough=True)
    if not 0 <= source_index < len(faces):
        raise ValueError(f"Source face index is unavailable ({len(faces)} faces detected).")
    identity = encode(recognizer, aligned_crop(actor, faces[source_index], ARCFACE_112, 112)[0])
    progress.update(300, label="Swapping the face")
    try:
        image, profile = read_photo(target)
    except OSError:
        raise ValueError("The target image could not be read.") from None
    point = target_point[1:] if target_point is not None else None
    if point is not None:
        face = face_at_point(image, point, detector)
    else:
        found = detect_faces(image, detector, thorough=True)
        if not len(found):
            raise ValueError("No face was found in the target image.")
        face = found[0]
    with ExitStack() as resources:
        mesh = resources.enter_context(create_mesh_detector(mesh_model)) if mesh_model is not None else None
        if mesh is not None:
            # Dense-mesh alignment points hold better than the detector's on
            # turned or tilted faces.
            refined, _ = mesh_five(image, face[4:14].reshape(5, 2), mesh)
            if refined is not None:
                face = face_from_points(refined, float(face[14]))
        crop, matrix = aligned_crop(image, face, ARCFACE_128, 256)
        labels = parse_face(parser, crop)
        blend = FaceBlend(mesh)
        alpha = mask_from_labels(image.shape, crop, matrix, labels,
                                 lambda crop, labels, alpha: blend.refine(crop, labels, alpha, 0., True), True,
                                 occlusion(occluder, crop))
    edited, roi = blend_swap(image, matrix, alpha, render(swapper, crop, identity), True, skin=skin_weight(labels))
    if roi is None:
        raise ValueError("The selected face could not be masked. Choose a clearer face.")
    delta = np.any(edited[roi] != image[roi], axis=2)
    if np.any(delta & (alpha[roi] == 0)):
        raise ValueError("Pixels outside the face mask changed.")
    progress.update(800, label="Verifying the lossless image")
    pending = output / "pending.png"
    options = {"icc_profile": profile} if profile else {}
    Image.fromarray(cv2.cvtColor(edited, cv2.COLOR_BGR2RGB)).save(pending, "PNG", **options)
    with Image.open(pending) as written:
        if not np.array_equal(cv2.cvtColor(np.asarray(written.convert("RGB")), cv2.COLOR_RGB2BGR), edited):
            raise ValueError("Lossless image verification failed.")
    pending.replace(output / "face-swap.png")
    report = {"kind": "image", "frames": 1, "swapped": int(delta.any()), "unchanged": int(not delta.any()),
              "width": image.shape[1], "height": image.shape[0], "image": "verified", "outside_mask": "byte exact"}
    (output / "verification.json").write_text(json.dumps(report))
    progress.finish()
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source","target","output","models"):
        cli.add_argument(name,type=Path)
    for name in ("source-index","target-index"):
        cli.add_argument("--"+name,type=int,default=0)
    cli.add_argument("--preview", action="store_true")
    cli.add_argument("--target-point", type=float, nargs=3, metavar=("SECONDS", "X", "Y"))
    cli.add_argument("--mesh-model", type=Path)
    cli.add_argument("--image", action="store_true", help="The target is a still image; write a verified PNG")
    args = cli.parse_args()
    try:
        if args.image:
            print(json.dumps(run_image(args.source, args.target, args.output, args.models, args.source_index,
                                       args.target_point, args.mesh_model)))
            cli.exit(0)
        print(json.dumps(run(args.source,args.target,args.output,args.models,args.source_index,args.target_index,
                             args.target_point,args.mesh_model)))
        if args.preview:
            status = Progress(1000, path=args.output / "progress")
            share = 1 - RENDER_SHARE - VERIFY_SHARE
            make_preview(args.output / "face-swap.mp4", args.output / "preview.mp4",
                         lambda frames, total: status.update(1000 * (1 - share + share * min(1, frames / max(total, 1))),
                                                             label="Preparing smooth playback"))
    except (ValueError, OSError) as error:
        cli.exit(1, f"{error}\n")
    except (Fail, RuntimeException) as error:
        detail = str(error).lower()
        if gpu_available() and any(text in detail for text in
                                   ("failed to allocate memory", "out of memory", "cudnn_status_alloc_failed")):
            # Replace the worker to release all CUDA arenas, including sessions held by
            # inference threads. The server can still cancel the same process group.
            os.execve(sys.executable, [sys.executable, "-B", *sys.argv],
                      {**os.environ, "FOOTAGE_FACE_CPU": "1"})
        raise
