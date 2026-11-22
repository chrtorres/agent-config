// Extending one cloth style across a whole outfit: helpers that sit beside the chain in
// cloth-collider.mjs. Dependency-free; metres and seconds; plain {x, y, z} objects.
//
//  - stepHem: a rigid garment piece (wide sleeve, tabard, hanging flap) that swings from a
//    pivot. One Verlet hem particle under gravity and air drag, pulled back toward the
//    rest shape by the cloth's stiffness, held at its length and limited to a cone so the
//    limb inside stays covered. The renderer then turns the pivot toward the hem.
//  - pullTowardRestLine: spring for a tied tail (ponytail, knotted cord) so it whips less
//    than loose silk and returns to hanging down the back.
//  - clampUnderCeiling: keeps particles below a hat or hood that the tail hangs under. The
//    ceiling must continue past the brim, or a tail thrown forward wraps around the edge
//    and rises above the hat.

export const HEM = Object.freeze({ drag: 1.4, stiffness: 30, cone: .3 });

/**
 * Advance one hanging hem by `h` seconds. `origin` is the pivot in world space, `rest` the
 * unit direction from pivot to hem in the current (animated) rest pose, `length` the
 * pivot-to-hem distance. `state` = { p, q }: current and previous hem. Mutates and returns.
 */
export function stepHem(state, { origin, rest, length, h }, tuning = HEM) {
  const { p, q } = state;
  const tx = origin.x + rest.x * length, ty = origin.y + rest.y * length, tz = origin.z + rest.z * length;
  const drag = Math.exp(-tuning.drag * h), k = tuning.stiffness * h * h;
  const vx = (p.x - q.x) * drag, vy = (p.y - q.y) * drag, vz = (p.z - q.z) * drag;
  q.x = p.x; q.y = p.y; q.z = p.z;
  p.x += vx + k * (tx - p.x);
  p.y += vy + k * (ty - p.y) - 9.81 * h * h;
  p.z += vz + k * (tz - p.z);
  let dx = p.x - origin.x, dy = p.y - origin.y, dz = p.z - origin.z;
  const d = Math.hypot(dx, dy, dz) || 1e-9;
  dx /= d; dy /= d; dz /= d;
  const cos = Math.max(-1, Math.min(1, dx * rest.x + dy * rest.y + dz * rest.z));
  if (Math.acos(cos) > tuning.cone) {
    // Back to the cone's edge, within the plane spanned by the rest and hem directions.
    let ox = dx - rest.x * cos, oy = dy - rest.y * cos, oz = dz - rest.z * cos;
    const o = Math.hypot(ox, oy, oz) || 1e-9;
    ox /= o; oy /= o; oz /= o;
    const c = Math.cos(tuning.cone), s = Math.sin(tuning.cone);
    dx = rest.x * c + ox * s; dy = rest.y * c + oy * s; dz = rest.z * c + oz * s;
  }
  p.x = origin.x + dx * length; p.y = origin.y + dy * length; p.z = origin.z + dz * length;
  return state;
}

/** Angle (radians) between the rest direction and the current hem direction. */
export function hemSwing(state, origin, rest) {
  const dx = state.p.x - origin.x, dy = state.p.y - origin.y, dz = state.p.z - origin.z;
  const d = Math.hypot(dx, dy, dz) || 1e-9;
  return Math.acos(Math.max(-1, Math.min(1, (dx * rest.x + dy * rest.y + dz * rest.z) / d)));
}

/**
 * Pull each chain particle toward a straight rest line from the root (`dir`, unit) with
 * stiffness `k` (1/s²), applied once per step after integration. For a tie at the root.
 */
export function pullTowardRestLine(chain, root, dir, k, h) {
  const a = k * h * h;
  chain.points.forEach((p, i) => {
    if (i === 0) return;
    const reach = chain.seg * i;
    p.x += a * (root.x + dir.x * reach - p.x);
    p.y += a * (root.y + dir.y * reach - p.y);
    p.z += a * (root.z + dir.z * reach - p.z);
  });
}

/**
 * Hat underside as a function of radial distance from the hat axis, in the head frame:
 * `surface(r)` inside the brim, then flat at brim height out to `reach`. Returns the
 * ceiling height or null where the hat no longer constrains the tail.
 */
export function hatCeiling(surface, brim, reach = brim * 3.3) {
  return (r) => (r > reach ? null : surface(Math.min(r, brim)));
}

/** Push particles (head-frame coordinates, y up) down to the ceiling. Returns moved count. */
export function clampUnderCeiling(points, ceiling, axis = { x: 0, z: 0 }) {
  let moved = 0;
  for (const p of points) {
    const limit = ceiling(Math.hypot(p.x - axis.x, p.z - axis.z));
    if (limit !== null && p.y > limit) { p.y = limit; moved++; }
  }
  return moved;
}
