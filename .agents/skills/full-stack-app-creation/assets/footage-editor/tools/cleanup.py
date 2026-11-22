"""Shared shape-edit kernel and the cleanup blend for overlapping features.

A shape edit scales the whole part uniformly about its tracked center, the
way a genuinely larger or smaller part would look. Only the surroundings
outside ``RING_START`` absorb the change, over a ring that widens with the
expansion so nothing folds. app/regions.mjs mirrors these formulas.
"""
import numpy as np

OVERLAP_STRENGTH = 1.35
STRONG_EDIT_RELIEF = .42
RING_START = .9
MIN_JACOBIAN = .3


def reach(adjustment):
    """Outer support radius, in units of the fitted ellipse radii.

    In the ring the displacement magnitude falls from grow*RING_START to zero
    along a smoothstep, whose steepest slope is 1.5/span. Keeping the radial
    Jacobian 1-1.5*grow*RING_START/span at MIN_JACOBIAN gives the span.
    """
    grow = max(0, *adjustment)
    return RING_START+max(.5, 1.5*grow*RING_START/(1-MIN_JACOBIAN))


def ring_weight(radius, outer):
    """1 in the uniformly scaled core, then RING_START*(1-smoothstep)/radius."""
    radius = np.maximum(radius, 1e-9)
    t = np.clip((radius-RING_START)/(outer-RING_START), 0, 1)
    return np.where(radius <= RING_START, 1, RING_START*(1-t*t*(3-2*t))/radius)


def feature_displacement(x, y, shapes, adjustment, mobility=1):
    """Displacement of one feature's segments, combined as a partition.

    Optional ``shape[6:8]`` is a soft-tissue offset in source pixels.
    Returns ``dx, dy, coverage``.
    """
    width, height = adjustment
    outer = reach(adjustment)
    dx, dy = np.zeros_like(x), np.zeros_like(y)
    total, complement = np.zeros_like(x), np.ones_like(x)
    for shape in shapes:
        if shape is None:
            continue
        cx, cy, ux, uy, rx, ry = shape[:6]
        ox, oy = (shape[6], shape[7]) if len(shape) >= 8 else (0, 0)
        px, py = x-cx, y-cy
        across = px*ux+py*uy
        along = py*ux-px*uy
        weight = ring_weight(np.sqrt((across/rx)**2+(along/ry)**2), outer)
        a, b = across*width, along*height
        dx += weight*(a*ux-b*uy+ox)
        dy += weight*(a*uy+b*ux+oy)
        total += weight
        complement *= 1-weight
    scale = mobility/np.maximum(1, total)
    return dx*scale, dy*scale, 1-complement


def group_fields(fields):
    """Group (shape, adjustment) pairs by feature.

    The exporter reuses one adjustment tuple for all segments of a feature.
    Separate features can have equal values, so group by tuple identity.
    """
    groups = {}
    for shape, adjustment in fields:
        if any(adjustment):
            groups.setdefault(id(adjustment), (adjustment, []))[1].append(shape)
    return groups


def displacement(x, y, fields):
    """Uncleaned displacement: independent features add together."""
    dx, dy = np.zeros_like(x), np.zeros_like(y)
    for adjustment, shapes in group_fields(fields).values():
        fx, fy, _ = feature_displacement(x, y, shapes, adjustment)
        dx += fx
        dy += fy
    return dx, dy


def stress(adjustment):
    scale = max(0,min(1,(max(abs(value) for value in adjustment)-.43)/.32))
    return scale**2*(3-2*scale)


def compile_cleanup(fields, pins=None):
    """Return a displacement function for (region, adjustment) pairs."""
    grouped = [(adjustment,shapes,stress(adjustment),(pins or {}).get(key,[]))
               for key,(adjustment,shapes) in group_fields(fields).items()]

    def cleaned(x, y):
        dx, dy = np.zeros_like(x), np.zeros_like(y)
        mass = np.zeros_like(x)
        pairs = np.zeros_like(x)
        strain = np.zeros_like(x)
        for adjustment,shapes,risk,anchors in grouped:
            mobility = np.ones_like(x)
            for ax,ay,radius in anchors:
                t = np.minimum(1,np.hypot(x-ax,y-ay)/radius)
                mobility *= t*t*(3-2*t)
            fx, fy, coverage = feature_displacement(x, y, shapes, adjustment, mobility)
            dx += fx
            dy += fy
            pairs += mass*coverage
            mass += coverage
            strain += risk*coverage**2

        # A feature contributes once regardless of how many segments it has.
        # Moderate isolated edits stay exact. Strong isolated edits soften locally.
        correction = 2*OVERLAP_STRENGTH*pairs+STRONG_EDIT_RELIEF*strain
        divisor = 1+np.divide(correction,mass,out=np.zeros_like(pairs),where=mass>0)
        return dx/divisor, dy/divisor

    return cleaned


def cleanup_displacement(x, y, fields):
    """Evaluate cleaned displacements over a NumPy grid."""
    return compile_cleanup(fields)(x,y)
