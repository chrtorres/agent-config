"""Soft-tissue dynamics for edited parts. Mirrors app/soft-body.mjs.

The footage already contains the original tissue's motion, so only the volume
a shape edit adds is simulated: that extra mass hangs from the tracked part on
a damped spring, lags when the body accelerates, and overshoots when it stops.
"""
import math

SOFT, FLESH, LIMB = (2.6, .2, 1), (3.2, .28, .7), (4.5, .35, .4)
# Natural frequency in Hz, damping ratio, softness. Rigid parts are absent.
MATERIALS = {
    "chest": SOFT, "left-breast": SOFT, "right-breast": SOFT,
    "buttocks": SOFT, "left-buttock": SOFT, "right-buttock": SOFT,
    "hips": FLESH, "left-hip": FLESH, "right-hip": FLESH, "torso": FLESH,
    "left-calf": (4, .3, .55), "right-calf": (4, .3, .55),
    "left-arm": LIMB, "right-arm": LIMB, "left-leg": LIMB, "right-leg": LIMB,
    "shoulders": (5, .4, .3),
}
LIMIT = .15
SMOOTH = (1, 4, 6, 4, 1)


def added_share(adjustment):
    width, height = adjustment
    grow = (1+width)*(1+height)-1
    return grow/(1+grow) if grow > 0 else 0


def _smoothed_centers(run, shapes):
    centers = []
    for position in range(len(run)):
        x = y = total = 0
        for tap in range(-2, 3):
            if not 0 <= position+tap < len(run):
                continue
            shape = shapes[run[position+tap]]
            weight = SMOOTH[tap+2]
            x += shape[0]*weight
            y += shape[1]*weight
            total += weight
        centers.append((x/total, y/total))
    return centers


def soft_body_track(frames, key, adjustment, manifest):
    """Per frame, a list of (ox, oy) per segment, or None for rigid parts."""
    material, share = MATERIALS.get(key), added_share(adjustment)
    if material is None or share <= 0:
        return None
    frequency, damping, softness = material
    omega, gain = 2*math.pi*frequency, share*softness
    times, fps = manifest.get("frameTimes"), manifest["fps"]

    def time(index):
        return times[index] if times is not None else index/fps

    segments = max([0, *(len(frame.get(key) or ()) for frame in frames)])
    result = [[None]*segments for _ in frames]
    for start, end in manifest.get("shots") or [[0, len(frames)]]:
        for segment in range(segments):
            shapes = [(frame.get(key) or ())[segment] if segment < len(frame.get(key) or ()) else None
                      for frame in frames]
            index = start
            while index < end:
                if shapes[index] is None:
                    index += 1
                    continue
                run = []
                while index < end and shapes[index] is not None:
                    run.append(index)
                    index += 1
                centers = _smoothed_centers(run, shapes)
                x, y = centers[0]
                vx = vy = 0
                result[run[0]][segment] = (0, 0)
                for step in range(1, len(run)):
                    dt = max(1e-4, time(run[step])-time(run[step-1]))
                    (ax, ay), (bx, by) = centers[step-1], centers[step]
                    cvx, cvy = (bx-ax)/dt, (by-ay)/dt
                    if step == 1:
                        vx, vy = cvx, cvy
                    substeps = max(1, math.ceil(dt*omega/.2))
                    h = dt/substeps
                    for sub in range(1, substeps+1):
                        cx, cy = ax+cvx*h*sub, ay+cvy*h*sub
                        vx += (-omega*omega*(x-cx)-2*damping*omega*(vx-cvx))*h
                        vy += (-omega*omega*(y-cy)-2*damping*omega*(vy-cvy))*h
                        x += vx*h
                        y += vy*h
                    shape = shapes[run[step]]
                    limit = LIMIT*min(shape[4], shape[5])
                    ox, oy = x-bx, y-by
                    size = math.hypot(ox, oy)
                    if size > limit:
                        keep = limit/size
                        ox, oy = ox*keep, oy*keep
                        x, y = bx+ox, by+oy
                        vx, vy = cvx+(vx-cvx)*keep, cvy+(vy-cvy)*keep
                    result[run[step]][segment] = (ox*gain, oy*gain)
    return result


def with_offsets(shapes, offsets):
    if offsets is None:
        return shapes
    return [(*shape[:6], *offsets[index]) if shape is not None and index < len(offsets) and offsets[index] is not None
            else shape for index, shape in enumerate(shapes)]
