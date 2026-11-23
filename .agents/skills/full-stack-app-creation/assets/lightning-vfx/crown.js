// A wide lightning crown around a character: counter-rotating helices parented to the
// character, plus world-space forked ground strikes, scorch rings and a burst shockwave.
// Geometry is static or preallocated; motion comes from uniforms and pooled rewrites.
import { createBoltMesh, forkPath } from "./lightning.js";

/** Radii are about 3–4.5× a 0.85 m character body radius; ~1 m coils read as cramped. */
export const DEFAULT_COILS = [
  { radius: 2.4, turns: 3.5, low: -0.3, high: 5.5, spin: 1.65, tint: 0x9ad8ff },
  { radius: 3.1, turns: 2.75, low: 0.2, high: 4.6, spin: -1.15, tint: 0xb9a4ff },
  { radius: 3.8, turns: 2.0, low: -0.1, high: 3.6, spin: 0.8, tint: 0x7fe6ff },
];

function helixGeometry(T, { radius, turns, low, high }, seed, segments = 160) {
  const positions = [], uvs = [], indices = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments,
      angle = t * Math.PI * 2 * turns + seed,
      r = radius * (1 + 0.1 * Math.sin(t * 13 + seed) + 0.03 * Math.sin(t * 127));
    const y = low + t * (high - low) + 0.08 * Math.sin(t * 153 + seed);
    for (const edge of [-1, 1]) {
      const w = r + edge * (0.16 + 0.05 * Math.sin(t * 31));
      positions.push(Math.cos(angle) * w, y, Math.sin(angle) * w);
      uvs.push((edge + 1) / 2, t);
    }
    if (i < segments) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeBoundingSphere();
  return geometry;
}

function coilMaterial(T, { spin, tint }) {
  // toneMapped:false with colors above 1 lets an existing bloom pass pick the coils up.
  return new T.ShaderMaterial({
    uniforms: { time: { value: 0 }, strength: { value: 1 }, spin: { value: spin }, tint: { value: new T.Color(tint) } },
    transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending, toneMapped: false,
    vertexShader: `uniform float time; uniform float spin; varying vec2 vUv;
      void main(){vUv=uv;vec3 p=position;float a=time*spin;
      p.xz=mat2(cos(a),-sin(a),sin(a),cos(a))*p.xz;
      float r=length(p.xz);
      float flare=.22*pow(max(0.,sin(p.y*3.1-time*9.0+r)),6.0);
      p.xz*=1.0+flare*.12;
      p.x+=.12*sin(p.y*13.0+time*7.0);p.z+=.09*cos(p.y*21.0-time*6.0);
      p.y+=.06*sin(r*9.0+time*11.0);
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    fragmentShader: `uniform float time;uniform float strength;uniform vec3 tint;varying vec2 vUv;
      void main(){
        float zig = 0.11 * sin(vUv.y * 119.0 + time * 3.0) + 0.06 * sin(vUv.y * 281.0 + time * 8.0);
        float d = abs(vUv.x - 0.5 - zig);
        float core = 1.0 - smoothstep(0.02, 0.09, d);
        float halo = 1.0 - smoothstep(0.05, 0.42, d);
        float flow = 0.6 + 0.4 * sin(vUv.y * 37.0 - time * 13.0);
        float burst = pow(max(0.0, sin(vUv.y * 9.0 - time * 5.0)), 8.0);
        float ends = smoothstep(0.0, 0.10, vUv.y) * smoothstep(0.0, 0.17, 1.0 - vUv.y);
        vec3 color = tint * halo * 0.9 + vec3(0.96, 0.93, 1.0) * core * (1.6 + burst * 2.0);
        gl_FragColor = vec4(color * strength, (halo * 0.26 + core * 0.6) * flow * ends * strength);
      }`,
  });
}

/**
 * character: Object3D the coils follow. world: scene-level parent for strikes.
 * ground(x, z) returns the walkable height; non-finite values fall back to the character's feet.
 * update({ active, intense, burst, reduced }, dt): active shows the coils, intense throws forks,
 * burst (one frame) fires the shockwave plus a fork on every pool slot, reduced holds a still pose.
 */
export function createEffectCrown(T, {
  character, world, ground = () => 0, rng = Math.random, coils = DEFAULT_COILS,
  forkCount = 8, strikeRing = [4, 9], scorchCount = 10, shockwaveRadius = 10, interval = [0.12, 0.35],
} = {}) {
  const owned = [];
  const own = (o) => (owned.push(o), o);
  const crown = new T.Group();
  crown.name = "EffectCrown";
  crown.visible = false;
  character.add(crown);
  const materials = coils.map((spec, i) => {
    const material = own(coilMaterial(T, spec));
    const ribbon = new T.Mesh(own(helixGeometry(T, spec, i * 2.1)), material);
    ribbon.name = `EffectCrownCoil_${i}`;
    ribbon.frustumCulled = false;
    crown.add(ribbon);
    return material;
  });
  const strikes = new T.Group();
  strikes.name = "EffectCrownStrikes";
  world.add(strikes);
  const forks = Array.from({ length: forkCount }, (_, i) => {
    const bolt = createBoltMesh(T, 96, { core: "#f6f2ff", glow: "#8fd3ff" });
    bolt.mesh.name = `EffectCrownFork_${i}`;
    own(bolt);
    strikes.add(bolt.mesh);
    return { ...bolt, age: Infinity, life: 0.3 };
  });
  const ringGeometry = own(new T.RingGeometry(0.94, 1, 96));
  const scorches = Array.from({ length: scorchCount }, (_, i) => {
    const ring = new T.Mesh(ringGeometry, own(new T.MeshBasicMaterial({
      color: 0xc9c2ff, transparent: true, opacity: 0, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    })));
    ring.name = `EffectCrownScorch_${i}`;
    ring.rotation.x = -Math.PI / 2;
    ring.visible = false;
    ring.userData = { age: 0, life: 1, radius: 1, from: 0.25 };
    strikes.add(ring);
    return ring;
  });
  const origin = new T.Vector3();
  let clock = 0, timer = 0;
  const groundAt = (x, z) => {
    const y = ground(x, z);
    return Number.isFinite(y) ? y : origin.y;
  };
  function fork(from, to) {
    // Reuse the oldest slot; idle slots carry an infinite age.
    let slot = forks[0];
    for (const f of forks) if (f.age > slot.age) slot = f;
    slot.write(forkPath(rng, from, to, { jag: 0.22, depth: 4, branches: 2, branchDepth: 3, width: 0.14, subBranches: 0 }));
    slot.age = 0;
    slot.mesh.visible = true;
  }
  function scorch(x, y, z, radius, life, from = 0.25) {
    let ring = scorches.find((r) => !r.visible);
    if (!ring) {
      ring = scorches[0];
      for (const r of scorches) if (r.userData.age / r.userData.life > ring.userData.age / ring.userData.life) ring = r;
    }
    Object.assign(ring.userData, { age: 0, life, radius, from });
    ring.position.set(x, y + 0.06, z);
    ring.visible = true;
  }
  function groundStrike(angle, distance) {
    const x = origin.x + Math.cos(angle) * distance, z = origin.z + Math.sin(angle) * distance;
    const y = groundAt(x, z);
    const coil = coils[Math.floor(rng() * coils.length)];
    fork([origin.x + Math.cos(angle) * coil.radius, origin.y + 2.5 + rng() * 2.5, origin.z + Math.sin(angle) * coil.radius], [x, y, z]);
    scorch(x, y, z, 1.5 + rng(), 0.35);
  }
  const reach = () => strikeRing[0] + rng() * (strikeRing[1] - strikeRing[0]);
  function update({ active = false, intense = false, burst = false, reduced = false } = {}, dt = 0) {
    dt = Math.min(Math.max(Number.isFinite(dt) ? dt : 0, 0), 0.1);
    crown.visible = active;
    if (!reduced) clock += dt;
    character.getWorldPosition(origin);
    const altitude = Math.min(1, Math.max(0, (origin.y - groundAt(origin.x, origin.z)) / 6));
    const strength = reduced ? 0.45 : (intense ? 1.1 : 0.8) + altitude * 0.5;
    for (const m of materials) {
      m.uniforms.time.value = clock;
      m.uniforms.strength.value = strength;
    }
    if (active && !reduced) {
      if (burst) {
        scorch(origin.x, groundAt(origin.x, origin.z), origin.z, shockwaveRadius, 0.6, 0);
        for (let i = 0; i < forks.length; i++) groundStrike((i / forks.length) * Math.PI * 2 + rng() * 0.4, reach());
        timer = 0.2;
      }
      timer -= dt;
      if (intense && timer <= 0) {
        groundStrike(rng() * Math.PI * 2, reach());
        timer = interval[0] + rng() * (interval[1] - interval[0]);
      }
    }
    for (const f of forks) {
      if (!f.mesh.visible) continue;
      f.age += dt;
      const p = f.age / f.life;
      f.mesh.visible = p < 1 && !reduced && active;
      f.uniforms.reveal.value = Math.min(1, f.age / 0.04);
      f.uniforms.intensity.value = Math.max(0, 1 - p) * (1.4 + Math.exp(-f.age * 20) * 2.5);
    }
    for (const ring of scorches) {
      if (!ring.visible) continue;
      const u = ring.userData;
      u.age += dt;
      const p = Math.min(1, u.age / u.life);
      ring.visible = p < 1 && !reduced && active;
      ring.scale.setScalar(Math.max(0.01, u.radius * (u.from + (1 - u.from) * (1 - (1 - p) ** 3))));
      ring.material.opacity = (1 - p) * 0.75;
    }
  }
  function dispose() {
    crown.removeFromParent();
    strikes.removeFromParent();
    for (const o of owned) o.dispose();
  }
  return { crown, strikes, forks, scorches, update, dispose };
}
