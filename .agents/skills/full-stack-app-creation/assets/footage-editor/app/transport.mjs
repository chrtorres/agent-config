// The frame boundary remains a simple rectangle and each interior triangle
// keeps its orientation. The resulting mesh transports a complete image.
const MIN_AREA_RATIO = .151;
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const cross = (ax, ay, bx, by) => ax * by - ay * bx;

export function edgeAxisWeight(value, extent, margin = Math.min(110, extent * .18)) {
  const t = clamp(Math.min(value, extent - value) / margin, 0, 1);
  return t * t * (3 - 2 * t);
}

export function edgeWeight(x, y, width, height) {
  const margin = Math.min(110, width * .18, height * .18);
  return edgeAxisWeight(x, width, margin) * edgeAxisWeight(y, height, margin);
}

export function fitTransport(positions, desired, indices, width, height) {
  if (!(width > 0 && height > 0) || positions.length !== desired.length)
    throw new RangeError("Transport geometry has invalid dimensions");

  const deltas = positions.map(([x, y], index) => {
    const [targetX, targetY] = desired[index];
    // Pin the boundary normal. Tangential motion is allowed along a frame
    // edge, and corners are fixed because they have two boundary normals.
    return [
      x === 0 || x === width || !Number.isFinite(targetX) ? 0 : clamp(targetX, 0, width) - x,
      y === 0 || y === height || !Number.isFinite(targetY) ? 0 : clamp(targetY, 0, height) - y,
    ];
  });
  let scale = 1;
  for (let i = 0; i < indices.length; i += 3) {
    const a = indices[i], b = indices[i + 1], c = indices[i + 2];
    const [x, y] = positions[a];
    const bx = positions[b][0] - x, by = positions[b][1] - y;
    const cx = positions[c][0] - x, cy = positions[c][1] - y;
    const area = cross(bx, by, cx, cy);
    if (Math.abs(area) < 1e-10) continue;

    const [dx, dy] = deltas[a];
    const ex = deltas[b][0] - dx, ey = deltas[b][1] - dy;
    const fx = deltas[c][0] - dx, fy = deltas[c][1] - dy;
    const linear = (cross(ex, ey, cx, cy) + cross(bx, by, fx, fy)) / area;
    const quadratic = cross(ex, ey, fx, fy) / area;
    const ratio = t => 1 + t * (linear + t * quadratic);
    // A triangle can fold and unfold as the displacement increases. Inspect
    // the quadratic's minimum before accepting the whole path to the target.
    const minimumAt = quadratic > 0 ? clamp(-linear / (2 * quadratic), 0, scale) : scale;
    if (ratio(minimumAt) >= MIN_AREA_RATIO) continue;

    let lo = 0, hi = minimumAt;
    for (let step = 0; step < 24; step++) {
      const mid = (lo + hi) / 2;
      if (ratio(mid) >= MIN_AREA_RATIO) lo = mid;
      else hi = mid;
    }
    scale = lo;
  }
  const points = positions.map(([x, y], index) => [
    x + deltas[index][0] * scale,
    y + deltas[index][1] * scale,
  ]);
  return {points, scale};
}
