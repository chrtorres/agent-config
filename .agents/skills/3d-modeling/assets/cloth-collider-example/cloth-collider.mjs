// A soft attachment (scarf tail, sash, ribbon) as a Verlet chain colliding with a body
// collider that is measured from the exported mesh and rides the moving bone.
// Dependency-free; units are metres and seconds. A renderer adapter supplies the bone's
// world transform each frame and draws the particle positions.

/**
 * Build a collider from a measured silhouette table: rows of
 * [height, back depth, half-width, front depth] in the bone's model frame, ascending.
 * Measure the rows from the delivered GLB (cape, robe, collar), not from a guess.
 */
export function makeProfile(rows, clearance = .03) {
  return function at(y) {
    if (y < rows[0][0] || y > rows.at(-1)[0]) return null;
    let i = 1;
    while (rows[i][0] < y) i++;
    const a = rows[i - 1], b = rows[i], t = (y - a[0]) / (b[0] - a[0] || 1);
    const lerp = (k) => a[k] + (b[k] - a[k]) * t + clearance;
    return { back: lerp(1), side: lerp(2), front: lerp(3) };
  };
}

/** Push a local point out of the ellipse at its height. `from` picks the exit side. */
export function pushOut(profile, p, from) {
  const e = profile(p.y);
  if (!e) return false;
  const depth = (z) => (z < 0 ? e.back : e.front);
  const f = (x, z) => (x / e.side) ** 2 + (z / depth(z)) ** 2;
  if (f(p.x, p.z) >= 1) return false;
  // Exit along the previous position's bearing, so fast cloth cannot tunnel to the front.
  const use = from && f(from.x, from.z) >= 1;
  let dx = use ? from.x : p.x, dz = use ? from.z : p.z;
  if (Math.hypot(dx, dz) < 1e-6) { dx = 0; dz = -1; }
  const k = 1 / Math.sqrt(f(dx, dz));
  p.x = dx * k; p.z = dz * k;
  return true;
}

/** Bone frame: origin, yaw (heading), pitch (forward lean), roll (bank). */
export function frame(origin, yaw, pitch, roll) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const cr = Math.cos(roll), sr = Math.sin(roll);
  // R = Ry(yaw) · Rz(roll) · Rx(pitch), columns are the local axes in world space.
  const Rx = [[1, 0, 0], [0, cp, -sp], [0, sp, cp]];
  const Rz = [[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]];
  const Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]];
  const mul = (A, B) => A.map((r) => [0, 1, 2].map((j) => r[0] * B[0][j] + r[1] * B[1][j] + r[2] * B[2][j]));
  const R = mul(mul(Ry, Rz), Rx);
  return {
    toLocal: (p) => {
      const d = [p.x - origin.x, p.y - origin.y, p.z - origin.z];
      return { x: R[0][0] * d[0] + R[1][0] * d[1] + R[2][0] * d[2],
        y: R[0][1] * d[0] + R[1][1] * d[1] + R[2][1] * d[2],
        z: R[0][2] * d[0] + R[1][2] * d[1] + R[2][2] * d[2] };
    },
    toWorld: (l) => ({ x: origin.x + R[0][0] * l.x + R[0][1] * l.y + R[0][2] * l.z,
      y: origin.y + R[1][0] * l.x + R[1][1] * l.y + R[1][2] * l.z,
      z: origin.z + R[2][0] * l.x + R[2][1] * l.y + R[2][2] * l.z }),
  };
}

/** A hanging chain of `segments` links totalling `length`, pinned at its root. */
export function makeChain(root, length = 1, segments = 12) {
  const seg = length / segments;
  const points = Array.from({ length: segments + 1 }, (_, i) => ({ x: root.x, y: root.y - i * seg, z: root.z }));
  return { points, previous: points.map((p) => ({ ...p })), seg };
}

/**
 * One fixed step: pin the root, integrate gravity and linear air drag, then alternate
 * length constraints with collision in the bone frame. `collide(point, previous)` mutates.
 */
export function stepChain(chain, root, h, collide, passes = 6) {
  const { points, previous, seg } = chain;
  Object.assign(points[0], root); Object.assign(previous[0], root);
  for (let i = 1; i < points.length; i++) {
    const p = points[i], q = previous[i], drag = Math.exp(-3.6 * h);
    const v = { x: p.x - q.x, y: p.y - q.y, z: p.z - q.z };
    Object.assign(q, p);
    p.x += v.x * drag; p.y += v.y * drag - 9.81 * h * h; p.z += v.z * drag;
  }
  for (let pass = 0; pass < passes; pass++) {
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1], b = points[i];
      const d = { x: b.x - a.x, y: b.y - a.y, z: b.z - a.z }, l = Math.hypot(d.x, d.y, d.z) || 1e-6;
      const k = (l - seg) / l, wa = i === 1 ? 0 : .5, wb = i === 1 ? 1 : .5;
      a.x += d.x * k * wa; a.y += d.y * k * wa; a.z += d.z * k * wa;
      b.x -= d.x * k * wb; b.y -= d.y * k * wb; b.z -= d.z * k * wb;
    }
    for (let i = 1; i < points.length; i++) collide(points[i], previous[i]);
  }
}
