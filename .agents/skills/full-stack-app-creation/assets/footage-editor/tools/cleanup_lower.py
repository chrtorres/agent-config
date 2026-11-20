"""Project observed thigh and shank axes into lower-limb cleanup fields."""
from math import hypot, isfinite

# MediaPipe IDs ordered proximal to distal on each side.
LEG_CHAINS = {"left": (23, 25, 27), "right": (24, 26, 28)}


def _axis(points, start_id, end_id, confidence, minimum_length):
    start, end = points.get(start_id), points.get(end_id)
    if start is None or end is None or len(start) < 3 or len(end) < 3:
        return None
    ax, ay, start_confidence = start[:3]
    bx, by, end_confidence = end[:3]
    if not all(isfinite(value) for value in (ax, ay, bx, by, start_confidence, end_confidence)):
        return None
    if min(start_confidence, end_confidence) < confidence:
        return None
    if hypot(bx - ax, by - ay) < minimum_length:
        return None
    return [ax, ay, bx, by]


def lower_anchors(points, regions):
    """Return projected endpoints in the same slots as each visible edit ellipse.

    Hip–knee and knee–ankle are separate segments. A missing or collapsed
    projection keeps its slot empty, and an existing region's visibility
    decision is preserved. The capsule ends at the ankle so lower-leg cleanup
    can leave the filmed foot/contact timing in place.
    """
    anchors = {}
    for side, (hip, knee, ankle) in LEG_CHAINS.items():
        key = f"{side}-leg"
        slots = regions.get(key)
        if slots:
            axes = (_axis(points, hip, knee, 25, 18), _axis(points, knee, ankle, 25, 18))
            anchors[key] = [
                axes[index] if ellipse is not None and index < len(axes) else None
                for index, ellipse in enumerate(slots)
            ]

        key = f"{side}-calf"
        slots = regions.get(key)
        if slots:
            axis = _axis(points, knee, ankle, 28, 22)
            anchors[key] = [axis if ellipse is not None else None for ellipse in slots]
    return anchors
