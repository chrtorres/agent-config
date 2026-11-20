"""Projected torso, pelvis, and head anchors for anatomy-aware cleanup."""

from math import hypot, isfinite


THORAX = ("shoulders", "chest", "left-breast", "right-breast")
PELVIS = ("hips", "left-hip", "right-hip", "buttocks", "left-buttock", "right-buttock")
FACE = ("left-eye", "right-eye", "left-brow", "right-brow", "nose", "mouth", "chin")


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _anchor(a, b, minimum):
    if a is None or b is None:
        return None
    x, y, u, v = (*a[:2], *b[:2])
    if not all(isfinite(value) for value in (x, y, u, v)) or hypot(u - x, v - y) < minimum:
        return None
    return [x, y, u, v]


def axial_anchors(points, regions):
    """Describe visible axial controls using per-frame source-pixel landmarks.

    Shoulder and pelvis landmarks approximate the projected thorax/pelvis
    references, rather than reconstructing a three-dimensional joint system.
    """
    def landmark(index, minimum_confidence=24):
        tracked = points.get(index)
        if tracked is not None and tracked[2] >= minimum_confidence:
            return tracked[:2]
        return None

    def pair(left, right, confidence=24):
        return landmark(right, confidence), landmark(left, confidence)

    shoulder_right, shoulder_left = pair(11, 12)
    hip_right, hip_left = pair(23, 24)
    shoulders = _anchor(shoulder_right, shoulder_left, 12)
    hips = _anchor(hip_right, hip_left, 12)
    spine = _anchor(
        _midpoint(shoulder_right, shoulder_left) if shoulders else None,
        _midpoint(hip_right, hip_left) if hips else None,
        20,
    )
    head = _anchor(*pair(7, 8), 10)

    def face_center(name):
        ellipses = regions.get(name, [])
        if ellipses and ellipses[0] is not None:
            return ellipses[0][:2]
        return None

    # Use the observed eye baseline for expression details. Mouth and eyebrow
    # centers retain their own observed animation relative to this head frame.
    face = _anchor(face_center("right-eye"), face_center("left-eye"), 10)
    anchors = {**dict.fromkeys(THORAX, shoulders), **dict.fromkeys(PELVIS, hips),
               **dict.fromkeys(FACE, face), "torso": spine, "head": head}

    return {
        key: [anchor if ellipse is not None else None for ellipse in regions[key]]
        for key, anchor in anchors.items()
        if key in regions
    }
