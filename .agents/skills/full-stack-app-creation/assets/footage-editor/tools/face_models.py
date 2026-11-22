"""Landmark alignment and inference adapted from the bundled photo face-swap example."""
from threading import Lock

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

# FaceFusion's ArcFace templates, normalized to the model crop width.
ARCFACE_112 = np.array([
    [0.34191607, 0.46157411], [0.65653393, 0.45983393],
    [0.50022500, 0.64050536], [0.37097589, 0.82469196],
    [0.63151696, 0.82325089],
], dtype=np.float32)
ARCFACE_128 = np.array([
    [0.36167656, 0.40387734], [0.63696719, 0.40235469],
    [0.50019687, 0.56044219], [0.38710391, 0.72160547],
    [0.61507734, 0.72034453],
], dtype=np.float32)
FACE_LABELS = (1, 2, 3, 4, 5, 10, 11, 12, 13)


def read_photo(path):
    with Image.open(path) as image:
        rgb = np.array(ImageOps.exif_transpose(image).convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), image.info.get("icc_profile")


# YuNet finds upright faces. Tilted heads and motion blur fall below its normal score, so a
# second pass tries rotated copies and a lower score before giving up on a frame.
FALLBACK_ANGLES = (30, -30, 60, -60, 90, -90, 180)
FALLBACK_SCORE = .55


def _detect_once(image, detector):
    height, width = image.shape[:2]
    scale = min(1.0, 1800 / max(height, width))
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image
    detector.setInputSize(small.shape[1::-1])
    _, faces = detector.detect(small)
    if faces is None:
        return np.empty((0, 15), np.float32)
    factors = np.array([width / small.shape[1], height / small.shape[0]], np.float32)
    faces = faces.copy()
    faces[:, :14] *= np.tile(factors, 7)
    return faces


def _rotated(image, angle):
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    size = int(height * sin + width * cos), int(height * cos + width * sin)
    matrix[:, 2] += (size[0] / 2 - width / 2, size[1] / 2 - height / 2)
    return cv2.warpAffine(image, matrix, size, borderMode=cv2.BORDER_REPLICATE), matrix


def _unrotate(faces, matrix):
    """Map faces found in a rotated copy back to the original image."""
    inverse = cv2.invertAffineTransform(matrix)
    mapped = faces.copy()
    for index, face in enumerate(faces):
        x, y, w, h = face[:4]
        corners = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float32)
        points = np.vstack((corners, face[4:14].reshape(5, 2)))
        points = points @ inverse[:, :2].T + inverse[:, 2]
        # The landmarks map exactly; the box becomes the upright bounds of the rotated box.
        left, top = points[:4].min(axis=0)
        right, bottom = points[:4].max(axis=0)
        mapped[index, :4] = left, top, right - left, bottom - top
        mapped[index, 4:14] = points[4:].reshape(-1)
    return mapped


def _overlap(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0., right - left) * max(0., bottom - top)
    return inter / max(1e-6, min(a[2] * a[3], b[2] * b[3]))


def _merge(groups):
    """Keep the highest-scoring detection of each face across passes."""
    candidates = sorted((face for faces in groups for face in faces), key=lambda face: -face[14])
    kept = []
    for face in candidates:
        if all(_overlap(face, other) < .5 for other in kept):
            kept.append(face)
    return np.array(kept, np.float32).reshape(-1, 15)


def detect_faces(image, detector, thorough=False, min_score=FALLBACK_SCORE):
    """Detect faces with five landmarks.

    The normal upright pass is used when it finds a face. Otherwise (or when `thorough`,
    for a single user-selected frame), rotated copies and a lower score threshold are tried,
    which recovers tilted, turned and motion-blurred faces.
    """
    faces = _detect_once(image, detector)
    if len(faces) and not thorough:
        return _sorted(faces)
    groups = [faces]
    threshold = detector.getScoreThreshold()
    try:
        detector.setScoreThreshold(min(threshold, min_score))
        groups.append(_detect_once(image, detector))
        for angle in FALLBACK_ANGLES:
            turned, matrix = _rotated(image, angle)
            found = _detect_once(turned, detector)
            if len(found):
                groups.append(_unrotate(found, matrix))
            if not thorough and sum(map(len, groups)):
                # A frame in a video only needs the first pass that finds a face.
                break
    finally:
        detector.setScoreThreshold(threshold)
    return _sorted(_merge(groups))


def _sorted(faces):
    if not len(faces):
        return []
    return faces[np.argsort(faces[:, 0] + faces[:, 2] / 2)]


def aligned_crop(image, face, template, size):
    points = face[4:14].reshape(5, 2)
    matrix, _ = cv2.estimateAffinePartial2D(
        points, template * size, method=cv2.RANSAC, ransacReprojThreshold=100
    )
    if matrix is None:
        raise ValueError("The facial landmarks could not be aligned.")
    crop = cv2.warpAffine(image, matrix, (size, size), borderMode=cv2.BORDER_REPLICATE)
    return crop, matrix


_GPU = None
_GPU_LOCK = Lock()


def gpu_available():
    """Load the pip-installed CUDA/cuDNN libraries once and report whether ONNX Runtime can use them."""
    global _GPU
    # Sessions are created from several threads; the lock keeps them from seeing a half-finished check.
    with _GPU_LOCK:
        if _GPU is None:
            ready = False
            if "CUDAExecutionProvider" in ort.get_available_providers():
                try:
                    # onnxruntime-gpu[cuda,cudnn] ships the libraries as wheels that are not on the
                    # loader path, so preload them before the first CUDA session.
                    ort.preload_dlls(cuda=True, cudnn=True, msvc=False)
                    ready = True
                except (AttributeError, OSError, RuntimeError):
                    ready = False
            _GPU = ready
        return _GPU


def session(path, threads=4):
    if not path.is_file():
        raise FileNotFoundError(f"Missing model {path.name}. Run fetch_models.py first.")
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    providers = ["CPUExecutionProvider"]
    if gpu_available():
        providers.insert(0, "CUDAExecutionProvider")
    return ort.InferenceSession(str(path), options, providers=providers)


def rgb_tensor(crop):
    return crop[:, :, ::-1].astype(np.float32).transpose(2, 0, 1)[None] / 255


def encode(recognizer, crop):
    tensor = rgb_tensor(crop) * 2 - 1
    vector = recognizer.run(None, {recognizer.get_inputs()[0].name: tensor})[0]
    return vector / np.linalg.norm(vector)


def render(swapper, crop, identity):
    feed = {"target": rgb_tensor(crop) * 2 - 1, "source": identity}
    for item in swapper.get_inputs():
        if item.type == "tensor(float16)":
            feed[item.name] = feed[item.name].astype(np.float16)
    pred = swapper.run(None, feed)[0][0].astype(np.float32)
    return np.clip(pred.transpose(1, 2, 0)[:, :, ::-1] * 127.5 + 127.5, 0, 255)


def parse_face(parser, crop):
    tensor = rgb_tensor(cv2.resize(crop, (512, 512)))
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)[None, :, None, None]
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)[None, :, None, None]
    logits = parser.run(None, {parser.get_inputs()[0].name: (tensor - mean) / std})[0][0]
    labels = logits.argmax(0).astype(np.uint8)
    return cv2.resize(labels, crop.shape[1::-1], interpolation=cv2.INTER_NEAREST)


def face_alpha(labels, feather):
    region = np.isin(labels, FACE_LABELS).astype(np.uint8)
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    # Remove stray islands and feather inward so the transition stays in the face.
    count, components, stats, _ = cv2.connectedComponentsWithStats(region)
    if count < 2:
        raise ValueError("The target face mask is empty.")
    main = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    region = (components == main).astype(np.uint8)
    region[[0, -1], :] = 0
    region[:, [0, -1]] = 0
    distance = cv2.distanceTransform(region, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    alpha = np.clip(distance / feather, 0, 1)
    return alpha * alpha * (3 - 2 * alpha)


def landmark_alpha(size, feather):
    """An oval face mask from the five-point alignment, for faces the parser cannot segment."""
    region = np.zeros((size, size), np.uint8)
    cv2.ellipse(region, (round(size * .5), round(size * .56)), (round(size * .32), round(size * .42)), 0, 0, 360, 1, -1)
    distance = cv2.distanceTransform(region, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    alpha = np.clip(distance / feather, 0, 1)
    return alpha * alpha * (3 - 2 * alpha)


def face_mask(parser, crop, feather):
    return face_alpha(parse_face(parser, crop), feather)


