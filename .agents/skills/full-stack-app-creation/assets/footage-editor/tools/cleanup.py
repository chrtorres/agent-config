"""Blend overlapping shape fields while keeping the original source warp."""
import numpy as np

OVERLAP_STRENGTH = 1.35
STRONG_EDIT_RELIEF = .42


def stress(adjustment):
    scale = max(0,min(1,(max(abs(value) for value in adjustment)-.43)/.32))
    return scale**2*(3-2*scale)


def compile_cleanup(fields, pins=None):
    """Return a displacement function for (region, adjustment) pairs.

    The exporter reuses one adjustment tuple for all segments of a feature.
    Separate features can have equal values, so group by tuple identity.
    """
    groups = {}
    for shape, adjustment in fields:
        if any(adjustment):
            groups.setdefault(id(adjustment), (adjustment, []))[1].append(shape)
    grouped = [(adjustment,shapes,stress(adjustment),(pins or {}).get(key,[]))
               for key,(adjustment,shapes) in groups.items()]

    def displacement(x, y):
        dx, dy = np.zeros_like(x), np.zeros_like(y)
        mass = np.zeros_like(x)
        pairs = np.zeros_like(x)
        strain = np.zeros_like(x)
        for (width,height),shapes,risk,anchors in grouped:
            complement = np.ones_like(x)
            mobility = np.ones_like(x)
            for ax,ay,radius in anchors:
                t = np.minimum(1,np.hypot(x-ax,y-ay)/radius)
                mobility *= t*t*(3-2*t)
            for cx, cy, ux, uy, rx, ry in shapes:
                px, py = x-cx, y-cy
                across = px*ux+py*uy
                along = py*ux-px*uy
                kernel = np.maximum(0, 1-(across/rx)**2-(along/ry)**2)**2
                complement *= 1-kernel
                a, b = across*width*kernel*mobility, along*height*kernel*mobility
                dx += a*ux-b*uy
                dy += a*uy+b*ux
            coverage = 1-complement
            pairs += mass*coverage
            mass += coverage
            strain += risk*coverage**2

        # A feature contributes once regardless of how many segments it has.
        # Moderate isolated edits stay exact. Strong isolated edits soften locally.
        correction = 2*OVERLAP_STRENGTH*pairs+STRONG_EDIT_RELIEF*strain
        divisor = 1+np.divide(correction,mass,out=np.zeros_like(pairs),where=mass>0)
        return dx/divisor, dy/divisor

    return displacement


def cleanup_displacement(x, y, fields):
    """Evaluate cleaned displacements over a NumPy grid."""
    return compile_cleanup(fields)(x,y)
