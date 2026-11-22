"""Refine face seams with motion-gated temporal samples and current eye detail."""
from collections import deque

import cv2
import numpy as np

if __package__:
    from .build_splats import TIME_SIGMA_FRAMES
    from .face_curvature import measure_landmarks
else:
    from build_splats import TIME_SIGMA_FRAMES
    from face_curvature import measure_landmarks


EYES = (
    (33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246),
    (362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398),
)


def eye_detail(labels, points):
    # Parser labels cover visible iris and sclera; mesh contours also locate
    # eyelids when a blink leaves few or no pixels classified as eyes.
    eyes = np.isin(labels, (4,5)).astype(np.uint8)
    if points is not None:
        size = np.array(labels.shape[::-1])
        for contour in EYES:
            vertices = np.rint(points[list(contour), :2] * size).astype(np.int32)
            cv2.fillPoly(eyes, [vertices], 1)
    return eyes


class FaceBlend:
    def __init__(self, detector=None):
        self.detector = detector
        self.history = deque(maxlen=2)
        self.steadied = 0
        self.eyes = 0
        self.rapid = 0

    def reset(self):
        self.history.clear()

    def refine(self, crop, labels, alpha, motion, cut):
        points = measure_landmarks(crop, self.detector) if self.detector is not None else None
        depth = points[[33, 263, 1, 61, 291], 2] if points is not None else None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
        luma = cv2.GaussianBlur(gray, (0,0), 1.4)
        if cut or motion >= .13:
            self.rapid += int(bool(self.history))
            self.reset()
        if self.history:
            # The aligned crop gives the image-plane coordinates of each
            # sample. Relative depth, photometric residual and time suppress
            # splats from a mismatched pose or a rapidly moving local edge.
            weighted, total = alpha.copy(), np.ones_like(alpha)
            for elapsed, (past_alpha, past_luma, past_depth) in enumerate(reversed(self.history), 1):
                dz = float(np.sqrt(np.mean((depth - past_depth)**2))) if depth is not None and past_depth is not None else 0.
                weight = np.exp(-.5 * (((luma-past_luma)/14)**2 + (dz/.045)**2
                                      + (elapsed/TIME_SIGMA_FRAMES)**2 + (motion/.07)**2))
                weighted += past_alpha * weight
                total += weight
            boundary = 4 * alpha * (1-alpha)
            refined = np.minimum(alpha, alpha + .7 * boundary * (weighted/total-alpha))
            self.steadied += int(np.any(refined < alpha - 1/255))
        else:
            refined = alpha
        self.history.append((alpha, luma, depth))
        eyes = eye_detail(labels, points)
        if eyes.any():
            self.eyes += 1
            distance = cv2.distanceTransform(1-eyes, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            feather = np.clip((distance-1.5)/5, 0, 1)
            refined = refined * feather**2 * (3-2*feather)
        return refined, eyes


def soften_color_seam(target, overlay, alpha):
    ring = (alpha >= .24) & (alpha <= .70)
    if np.count_nonzero(ring) < 32:
        return overlay
    delta = np.clip(np.median(target[ring] - overlay[ring], axis=0), -20, 20)
    return np.clip(overlay + delta * (.65 * (1-alpha[..., None])**2), 0, 255)
