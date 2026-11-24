"""Refine face seams with motion-gated temporal samples and current eye and mouth detail.

The swap generator redraws the whole face, including the inside of the mouth.
It renders teeth soft, loses the tongue and lags open-mouth shapes, so a
smile, speech or a stuck-out tongue looks smeared or wrong. The performer's
own mouth interior (teeth, tongue, cavity) carries no identity, so it is kept
from the current frame, like the eyes, while the generated lips surround it.
"""
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

# Inner and outer lip contours of the 468-point face mesh.
INNER_LIPS = (78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95)
OUTER_LIPS = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146)
MOUTH_LABEL, LIP_LABELS, SKIN_LABEL = 11, (12, 13), 1
# Labels a tongue may not extend over: background, clothes, hair and hats.
NOT_FACE = (0, 16, 17, 18)


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


def _polygon(points, contour, size):
    mask = np.zeros(size[::-1], np.uint8)
    cv2.fillPoly(mask, [np.rint(points[list(contour), :2]*size).astype(np.int32)], 1)
    return mask


def tongue_detail(crop, labels, lips, interior, ocular):
    """Tongue pixels outside the lips, joined to the mouth opening.

    The parser labels a stuck-out tongue as skin or lip, so it is found by
    colour: redder than the surrounding skin (CIELAB a*), outside the lips,
    and touching their edge. A short bridge across the lip band connects it
    to the mouth opening, where the lip is hidden behind the tongue.
    """
    skin = (labels == SKIN_LABEL) & ~cv2.dilate(lips, np.ones((5, 5), np.uint8)).astype(bool)
    rows, _ = np.nonzero(lips)
    if not rows.size or np.count_nonzero(skin) < 50:
        return np.zeros_like(lips)
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    redness = lab[..., 1]
    # Compare with skin around the mouth, which is lit like the tongue.
    near = skin & (np.abs(np.arange(lips.shape[0])[:, None]-rows.mean()) < ocular)
    skin_red = float(np.median(redness[near if np.count_nonzero(near) > 50 else skin]))
    lip_pixels = lips.astype(bool) & ~interior.astype(bool)
    lip_red = float(np.median(redness[lip_pixels])) if np.count_nonzero(lip_pixels) > 20 else skin_red+16
    threshold = skin_red+max(7., .5*(lip_red-skin_red))
    # Search close above and beside the lips and further below them.
    distance = cv2.distanceTransform(1-lips, cv2.DIST_L2, 3)
    below = np.arange(lips.shape[0])[:, None] > rows.mean()
    reach = np.where(below, .9*ocular, .2*ocular)
    candidate = ((redness > threshold) & (distance > 0) & (distance < reach) & ~np.isin(labels, NOT_FACE)).astype(np.uint8)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    edge = cv2.dilate(lips, np.ones((7, 7), np.uint8)) & ~lips.astype(bool)
    count, components, stats, _ = cv2.connectedComponentsWithStats(candidate)
    tongue = np.zeros_like(lips)
    for index in range(1, count):
        part = components == index
        # A tongue touches the lips and reaches well past them. A thin red rim
        # left by a slightly small lip contour does neither.
        if (stats[index, cv2.CC_STAT_AREA] < max(20, .006*ocular**2) or not np.any(part & edge.astype(bool))
                or distance[part].max() < .06*ocular):
            continue
        tongue[part] = 1
        # Bridge: the hull of the outside part and the opening above or beside it, kept within the lips.
        left, width = stats[index, cv2.CC_STAT_LEFT], stats[index, cv2.CC_STAT_WIDTH]
        joined = part.copy()
        joined[:, left:left+width] |= interior[:, left:left+width].astype(bool)
        if not interior[:, left:left+width].any():
            joined[:, left:left+width] |= lips[:, left:left+width].astype(bool)
        hull = np.zeros_like(lips)
        cv2.fillConvexPoly(hull, cv2.convexHull(np.argwhere(joined)[:, ::-1].astype(np.int32)), 1)
        tongue |= hull & lips
    return tongue


def mouth_detail(crop, labels, points):
    """Current-frame mouth interior (teeth, cavity, tongue) in crop pixels.

    Returns (interior, tongue) as uint8 masks; tongue is the part outside the lips.
    """
    size = np.array(labels.shape[::-1])
    interior = (labels == MOUTH_LABEL).astype(np.uint8)
    if points is not None:
        opening = _polygon(points, INNER_LIPS, size)
        ocular = float(np.linalg.norm((points[263, :2]-points[33, :2])*size))
        gap = float(np.linalg.norm((points[14, :2]-points[13, :2])*size))
        # The mesh keeps a thin inner contour even on closed lips. Treat it as
        # an opening only when the lips are apart or the parser sees the mouth.
        area = np.count_nonzero(opening)
        if gap > .06*ocular or np.count_nonzero(interior) >= max(12, .2*area):
            interior |= opening
        lips = _polygon(points, OUTER_LIPS, size) | interior
    else:
        lips = np.isin(labels, (MOUTH_LABEL, *LIP_LABELS)).astype(np.uint8)
        if lips.any():
            lips = cv2.morphologyEx(lips, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        ocular = .27*labels.shape[1]
    if np.count_nonzero(interior) < 6:
        interior[:] = 0
    tongue = tongue_detail(crop, labels, lips, interior, ocular) if lips.any() else np.zeros_like(interior)
    return interior, tongue


class FaceBlend:
    def __init__(self, detector=None):
        self.detector = detector
        self.history = deque(maxlen=2)
        self.steadied = 0
        self.eyes = 0
        self.rapid = 0
        self.mouths = 0
        self.tongues = 0

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
        # The mouth interior also comes from the current frame only, so an
        # opening or closing mouth never shows a stale hole.
        interior, tongue = mouth_detail(crop, labels, points)
        mouth = interior | tongue
        if mouth.any():
            self.mouths += int(interior.any())
            self.tongues += int(tongue.any())
            distance = cv2.distanceTransform(1-mouth, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            feather = np.clip((distance-.5)/3, 0, 1)
            refined = refined * feather**2 * (3-2*feather)
        return refined, eyes | mouth


def soften_color_seam(target, overlay, alpha):
    ring = (alpha >= .24) & (alpha <= .70)
    if np.count_nonzero(ring) < 32:
        return overlay
    # Match colour on the outer face edge only. The rings around the kept eyes
    # and mouth border teeth, cavity and sclera, which would bias the shift.
    count, components, stats, _ = cv2.connectedComponentsWithStats(ring.astype(np.uint8))
    if count > 2:
        ring = components == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    delta = np.clip(np.median(target[ring] - overlay[ring], axis=0), -20, 20)
    return np.clip(overlay + delta * (.65 * (1-alpha[..., None])**2), 0, 255)
