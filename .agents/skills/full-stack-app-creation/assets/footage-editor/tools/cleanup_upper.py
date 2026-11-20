"""Source-plane joint frames for both upper limbs and hand subparts.

The anatomical hierarchy follows the shoulder, elbow, wrist and hand joint
systems described by Wu et al. (2005), doi:10.1016/j.jbiomech.2004.05.042.
The clip supplies projected landmarks, so these frames describe image motion.
"""
import math


_ARM_JOINTS = {"left": (11, 13, 15), "right": (12, 14, 16)}
_DIGITS = ("thumb", "index-finger", "middle-finger", "ring-finger", "pinky")


def _bone(points, start, end, confidence=28):
    a, b = points.get(start), points.get(end)
    if a is None or b is None or min(a[2], b[2]) < confidence:
        return None
    if math.dist(a[:2], b[:2]) < 12:
        return None
    return [*a[:2], *b[:2]]


def _observed_frame(shape):
    if shape is None:
        return None
    x, y, ux, uy, _, along_radius = shape
    norm = math.hypot(ux, uy)
    if norm < .5 or along_radius < 1:
        return None
    # The existing hand fitter sets the ellipse's width normal from the
    # wrist-to-palm/digit direction. Recover that directed long axis.
    dx, dy = uy/norm*along_radius, -ux/norm*along_radius
    return [x, y, x+dx, y+dy]


def _first(regions, key):
    shapes = regions.get(key)
    return shapes[0] if shapes else None


def _palm_parent(points, elbow, wrist, palm):
    observed = _observed_frame(palm)
    if observed is None:
        return None
    forearm = _bone(points, elbow, wrist, confidence=40)
    if forearm is None:
        return observed

    x, y, end_x, end_y = observed
    along_radius = palm[5]
    palm_x, palm_y = (end_x-x)/along_radius, (end_y-y)/along_radius
    ex, ey, wx, wy = forearm
    # A projected pose wrist and a detailed hand detection can disagree
    # under overlap or occlusion. Adopt the forearm frame only when the
    # observed palm sits in a plausible neighborhood of that wrist.
    dx, dy = x-wx, y-wy
    along = dx*palm_x + dy*palm_y
    across = dy*palm_x - dx*palm_y
    if not (.08*along_radius <= along <= 1.5*along_radius and abs(across) <= max(7, .75*palm[4])):
        return observed
    forearm_length = math.hypot(wx-ex, wy-ey)
    if forearm_length < 24:
        return observed
    # Normalizing to the observed support avoids treating forearm foreshortening
    # as a change in palm size. Wrist flex survives as motion in this frame.
    scale = along_radius/forearm_length
    return [wx, wy, wx+(wx-ex)*scale, wy+(wy-ey)*scale]


def upper_anchors(points, regions):
    """Return one directed [ax, ay, bx, by] anchor per visible ellipse slot.

    Upper-arm and forearm slots retain their individual proximal bone frames.
    Palm cleanup can follow the pose wrist; digits follow the observed palm so
    a real curl or extension remains a local change rather than camera jitter.
    """
    anchors = {}
    shoulders = regions.get("shoulders")
    if shoulders:
        shoulder_axis = _bone(points, 12, 11, confidence=36)
        anchors["shoulders"] = [shoulder_axis if shape is not None else None for shape in shoulders]

    for side, (shoulder, elbow, wrist) in _ARM_JOINTS.items():
        arm_key = f"{side}-arm"
        arm_shapes = regions.get(arm_key)
        if arm_shapes:
            bones = ((shoulder, elbow), (elbow, wrist))
            anchors[arm_key] = [
                _bone(points, *bones[index]) if shape is not None and index < len(bones) else None
                for index, shape in enumerate(arm_shapes)
            ]

        palm_key = f"{side}-hand"
        palm = _first(regions, palm_key)
        palm_axis = _observed_frame(palm)
        if palm_key in regions:
            basis = _palm_parent(points, elbow, wrist, palm)
            anchors[palm_key] = [basis if shape is not None else None for shape in regions[palm_key]]

        for digit in _DIGITS:
            key = f"{side}-{digit}"
            if key in regions:
                anchors[key] = [
                    palm_axis or _observed_frame(shape) if shape is not None else None
                    for shape in regions[key]
                ]
    return anchors
