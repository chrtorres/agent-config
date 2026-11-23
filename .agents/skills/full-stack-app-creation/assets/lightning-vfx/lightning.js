// Forked lightning: pure path generation plus pooled, camera-facing ribbon meshes.
// No DOM. GPU buffers are preallocated and rewritten only when a bolt strikes; a path
// larger than a mesh's capacity keeps its leading channels and drops the rest.

export function seededRandom(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function displace(rng, points, a, b, depth, jag) {
  if (depth === 0) return;
  const [ax, ay, az] = points[a], [bx, by, bz] = points[b];
  const len = Math.hypot(bx - ax, by - ay, bz - az);
  const mid = [
    (ax + bx) / 2 + (rng() - 0.5) * len * jag * 2,
    (ay + by) / 2 + (rng() - 0.5) * len * jag,
    (az + bz) / 2 + (rng() - 0.5) * len * jag * 2,
  ];
  points.splice(b, 0, mid);
  // The right half sits after the inserted midpoint, so subdivide it first.
  displace(rng, points, b, b + 1, depth - 1, jag);
  displace(rng, points, a, b, depth - 1, jag);
}

function channel(rng, from, to, depth, jag) {
  const points = [from.slice(), to.slice()];
  displace(rng, points, 0, 1, depth, jag);
  return points;
}

/** Main channel plus recursive side branches: [{ points, width, level }], main first. */
export function forkPath(rng, from, to, { jag = 0.2, depth = 6, branches = 4, branchDepth = 4, width = 0.4, subBranches = 1 } = {}) {
  const main = channel(rng, from, to, depth, jag);
  const out = [{ points: main, width, level: 0 }];
  const grow = (parent, count, level, w) => {
    for (let i = 0; i < count; i++) {
      const at = 1 + Math.floor(rng() * (parent.length - 2) * 0.8);
      const start = parent[at], next = parent[Math.min(parent.length - 1, at + 1)];
      const dir = [next[0] - start[0], next[1] - start[1], next[2] - start[2]];
      const reach = (0.25 + rng() * 0.35) * Math.hypot(to[0] - from[0], to[1] - from[1], to[2] - from[2]) / (level + 1);
      const dl = Math.hypot(...dir) || 1;
      const spread = 0.6 + rng() * 0.9, side = rng() < 0.5 ? -1 : 1;
      const end = [
        start[0] + (dir[0] / dl + side * spread * (rng() - 0.2)) * reach,
        start[1] + (dir[1] / dl - 0.35) * reach,
        start[2] + (dir[2] / dl - side * spread * (rng() - 0.2)) * reach,
      ];
      const pts = channel(rng, start, end, Math.max(2, branchDepth - level), jag * 1.15);
      out.push({ points: pts, width: w, level: level + 1 });
      if (level + 1 <= subBranches) grow(pts, rng() < 0.6 ? 1 : 0, level + 1, w * 0.55);
    }
  };
  grow(main, branches, 0, width * 0.5);
  return out;
}

/** Uniform strike position on an annulus around the center. */
export function strikePoint(rng, cx, cz, min = 15, max = 70) {
  const angle = rng() * Math.PI * 2;
  const distance = Math.sqrt(min * min + rng() * (max * max - min * min));
  return { x: cx + Math.cos(angle) * distance, z: cz + Math.sin(angle) * distance, distance, angle };
}

/** Real lightning re-strikes its channel: a main stroke and two fading return strokes. */
export function boltEnvelope(t) {
  if (t < 0) return 0;
  return Math.exp(-t * 16)
    + (t > 0.085 ? 0.8 * Math.exp(-(t - 0.085) * 12) : 0)
    + (t > 0.23 ? 0.45 * Math.exp(-(t - 0.23) * 13) : 0);
}

const vertexShader = `
  attribute vec3 tangent3; attribute float side; attribute float along; attribute float level;
  varying float vSide; varying float vAlong; varying float vLevel;
  void main(){
    vec4 world = modelMatrix * vec4(position, 1.0);
    vec3 view = normalize(cameraPosition - world.xyz);
    vec3 t = normalize(mat3(modelMatrix) * tangent3 + vec3(1e-5));
    vec3 across = normalize(cross(t, view) + vec3(0.0, 1e-5, 0.0));
    world.xyz += across * side;
    vSide = sign(side); vAlong = along; vLevel = level;
    gl_Position = projectionMatrix * viewMatrix * world;
  }`;
const fragmentShader = `
  uniform float intensity; uniform float reveal; uniform vec3 core; uniform vec3 glow;
  varying float vSide; varying float vAlong; varying float vLevel;
  void main(){
    if (vAlong > reveal) discard;
    float d = abs(vSide);
    float hot = 1.0 - smoothstep(0.0, 0.32, d);
    float halo = 1.0 - smoothstep(0.15, 1.0, d);
    float branchFade = 1.0 / (1.0 + vLevel * 1.4);
    float tip = 1.0 + smoothstep(reveal - 0.05, reveal, vAlong) * 0.8;
    vec3 color = core * hot * 2.4 + glow * halo * 0.9;
    gl_FragColor = vec4(color * intensity * branchFade * tip, (hot * 0.9 + halo * 0.45) * min(1.0, intensity) * branchFade);
  }`;

/** One pooled bolt: a fixed-capacity ribbon whose buffers are rewritten per strike. */
export function createBoltMesh(T, capacity = 256, { core = "#f4efff", glow = "#8f7dff" } = {}) {
  const verts = capacity * 2;
  const geometry = new T.BufferGeometry();
  const attr = (n) => new T.BufferAttribute(new Float32Array(verts * n), n).setUsage(T.DynamicDrawUsage);
  geometry.setAttribute("position", attr(3));
  geometry.setAttribute("tangent3", attr(3));
  geometry.setAttribute("side", attr(1));
  geometry.setAttribute("along", attr(1));
  geometry.setAttribute("level", attr(1));
  geometry.setIndex(new T.BufferAttribute(new Uint32Array(capacity * 6), 1).setUsage(T.DynamicDrawUsage));
  geometry.setDrawRange(0, 0);
  const uniforms = {
    intensity: { value: 0 }, reveal: { value: 1 },
    core: { value: new T.Color(core) }, glow: { value: new T.Color(glow) },
  };
  const material = new T.ShaderMaterial({
    uniforms, vertexShader, fragmentShader, transparent: true, depthWrite: false,
    blending: T.AdditiveBlending, toneMapped: false, side: T.DoubleSide, fog: false,
  });
  const mesh = new T.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.visible = false;
  mesh.castShadow = mesh.receiveShadow = false;
  function write(paths) {
    const pos = geometry.attributes.position.array, tan = geometry.attributes.tangent3.array;
    const side = geometry.attributes.side.array, along = geometry.attributes.along.array;
    const lvl = geometry.attributes.level.array, index = geometry.index.array;
    let v = 0, n = 0;
    for (const { points, width, level } of paths) {
      if (v / 2 + points.length > capacity) break;
      const first = v / 2;
      for (let i = 0; i < points.length; i++) {
        const p = points[i], a = points[Math.max(0, i - 1)], b = points[Math.min(points.length - 1, i + 1)];
        const u = i / (points.length - 1);
        // Branches start part-way down the main channel and taper to a point.
        const reach = level ? 0.25 + u * 0.75 : u;
        const w = width * (level ? 1 - u * 0.85 : 1 - u * 0.35);
        for (const s of [-1, 1]) {
          pos.set(p, v * 3);
          tan.set([b[0] - a[0], b[1] - a[1], b[2] - a[2]], v * 3);
          side[v] = s * w;
          along[v] = reach;
          lvl[v] = level;
          v++;
        }
        if (i < points.length - 1) {
          const k = (first + i) * 2;
          index.set([k, k + 1, k + 2, k + 1, k + 3, k + 2], n);
          n += 6;
        }
      }
    }
    for (const name of ["position", "tangent3", "side", "along", "level"]) geometry.attributes[name].needsUpdate = true;
    geometry.index.needsUpdate = true;
    geometry.setDrawRange(0, n);
    return { vertices: v, indices: n };
  }
  return { mesh, uniforms, write, capacity, dispose() { geometry.dispose(); material.dispose(); } };
}

/** Sky-to-ground and cloud-to-cloud strikes around a focus point. */
export function createLightningField(T, scene, { count = 6, rng = Math.random, ground = () => 0 } = {}) {
  const group = new T.Group();
  group.name = "Sky lightning";
  scene.add(group);
  const bolts = Array.from({ length: count }, (_, i) => {
    const bolt = createBoltMesh(T, 320);
    bolt.mesh.name = `SkyBolt_${i}`;
    group.add(bolt.mesh);
    return { ...bolt, age: Infinity, life: 0.75, distance: Infinity, x: 0, y: 0, z: 0, weight: 0 };
  });
  let cursor = 0;
  function strike(cx, cz, { min = 15, max = 70, cloud = false } = {}) {
    const bolt = bolts[cursor++ % bolts.length];
    const at = strikePoint(rng, cx, cz, min, max);
    const floor = ground(at.x, at.z);
    let from, to;
    if (cloud) {
      const y = floor + 55 + rng() * 25, half = 20 + rng() * 25, a = rng() * Math.PI;
      from = [at.x - Math.cos(a) * half, y, at.z - Math.sin(a) * half];
      to = [at.x + Math.cos(a) * half, y + (rng() - 0.5) * 10, at.z + Math.sin(a) * half];
    } else {
      from = [at.x + (rng() - 0.5) * 24, floor + 60 + rng() * 25, at.z + (rng() - 0.5) * 24];
      to = [at.x, floor, at.z];
    }
    // Width grows with distance so far bolts still read through rain and fog.
    const width = 0.3 + at.distance * 0.012;
    bolt.write(forkPath(rng, from, to, {
      jag: cloud ? 0.16 : 0.2, depth: 6, branches: cloud ? 6 : 3 + Math.floor(rng() * 4),
      branchDepth: 4, width, subBranches: 2,
    }));
    bolt.age = 0;
    bolt.life = 0.75;
    bolt.distance = at.distance;
    bolt.x = to[0]; bolt.y = to[1]; bolt.z = to[2];
    bolt.weight = cloud ? 0.35 : 1;
    bolt.mesh.visible = true;
    return { x: bolt.x, y: bolt.y, z: bolt.z, distance: at.distance, cloud };
  }
  /** Advances bolts; returns the strongest proximity-weighted flash and where it struck. */
  function update(dt) {
    let level = 0, nearest = null;
    for (const bolt of bolts) {
      if (!bolt.mesh.visible) continue;
      bolt.age += dt;
      if (bolt.age >= bolt.life) { bolt.mesh.visible = false; bolt.uniforms.intensity.value = 0; continue; }
      const env = boltEnvelope(bolt.age);
      // The leader races down in ~60 ms, then the whole channel stays lit for the return strokes.
      bolt.uniforms.reveal.value = Math.min(1, bolt.age / 0.06);
      bolt.uniforms.intensity.value = 0.35 + env * 2.2;
      const near = 1 - Math.min(1, Math.max(0, (bolt.distance - 15) / 55));
      const flash = env * bolt.weight * (0.35 + 0.65 * near);
      if (flash > level) { level = flash; nearest = bolt; }
    }
    return { level, strike: nearest && { x: nearest.x, y: nearest.y, z: nearest.z, distance: nearest.distance } };
  }
  return {
    group, bolts, strike, update,
    set visible(v) { group.visible = v; },
    dispose() { for (const b of bolts) b.dispose(); group.removeFromParent(); },
  };
}
