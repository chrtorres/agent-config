// Behavioral tests for the bundled lightning VFX. They run without installing three:
// the pure path/RNG functions need nothing, and the mesh/pool logic runs against a
// small faithful three stub (three-stub.mjs) so the buffer math stays honest.
import test from "node:test";
import assert from "node:assert/strict";
import T from "./three-stub.mjs";
import { boltEnvelope, createBoltMesh, createLightningField, forkPath, seededRandom, strikePoint } from "./lightning.js";
import { createEffectCrown, DEFAULT_COILS } from "./crown.js";
import { resolveStartMode } from "./start-mode.js";

test("forkPath is deterministic per seed, bounded, and branches within limits", () => {
  const a = forkPath(seededRandom(11), [0, 80, 0], [0, 0, 0], { branches: 5, subBranches: 1 });
  const b = forkPath(seededRandom(11), [0, 80, 0], [0, 0, 0], { branches: 5, subBranches: 1 });
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, forkPath(seededRandom(12), [0, 80, 0], [0, 0, 0], { branches: 5, subBranches: 1 }));
  assert.equal(a[0].level, 0);
  assert.equal(a[0].points.length, 65);
  assert.deepEqual(a[0].points[0], [0, 80, 0]);
  assert.deepEqual(a[0].points.at(-1), [0, 0, 0]);
  assert.equal(a.filter((p) => p.level === 1).length, 5);
  assert.ok(a.length <= 11);
  for (const { points } of a) for (const [x, y, z] of points) {
    assert.ok(Math.hypot(x, z) < 60);
    assert.ok(y > -40 && y < 120);
  }
});

test("strike points stay on the min–max annulus and cover every direction", () => {
  const rng = seededRandom(5), quadrants = new Set();
  for (let i = 0; i < 400; i++) {
    const p = strikePoint(rng, 10, -4);
    const d = Math.hypot(p.x - 10, p.z + 4);
    assert.ok(d >= 15 - 1e-9 && d <= 70 + 1e-9);
    assert.ok(Math.abs(d - p.distance) < 1e-9);
    quadrants.add(`${Math.sign(p.x - 10)}${Math.sign(p.z + 4)}`);
  }
  assert.equal(quadrants.size, 4);
});

test("bolt envelope re-strikes its channel and fades", () => {
  assert.equal(boltEnvelope(-1), 0);
  assert.ok(boltEnvelope(0) > 0.99);
  assert.ok(boltEnvelope(0.09) > boltEnvelope(0.08), "a return stroke re-brightens");
  assert.ok(boltEnvelope(0.75) < 0.02);
});

test("bolt mesh rewrites a fixed buffer, keeps the main channel and drops overflow branches", () => {
  const bolt = createBoltMesh(T, 90);
  const buffer = bolt.mesh.geometry.attributes.position.array;
  const big = forkPath(seededRandom(2), [0, 50, 0], [0, 0, 0], { depth: 6, branches: 4 });
  assert.ok(big.reduce((n, p) => n + p.points.length, 0) > 90, "fixture overflows capacity");
  const result = bolt.write(big);
  assert.ok(result.vertices >= 65 * 2 && result.vertices <= 180);
  assert.equal(bolt.mesh.geometry.attributes.position.array, buffer, "the GPU buffer is reused, not reallocated");
  assert.equal(bolt.mesh.geometry.drawRange.count, result.indices);
  const index = bolt.mesh.geometry.index.array.subarray(0, result.indices);
  assert.ok(Math.max(...index) < result.vertices, "indices stay inside written vertices");
  assert.ok(result.indices >= 64 * 6, "the main channel is one unbroken strip");
  const again = bolt.write(forkPath(seededRandom(3), [0, 20, 0], [0, 0, 0], { depth: 3, branches: 0 }));
  assert.equal(again.vertices, 18);
  assert.equal(bolt.mesh.geometry.attributes.position.array, buffer);
  bolt.dispose();
  assert.ok(bolt.mesh.geometry.disposed && bolt.mesh.material.disposed);
});

test("sky lightning pools a fixed count, lands on the ground, and reports proximity flash", () => {
  const scene = new T.Scene();
  const field = createLightningField(T, scene, { count: 6, rng: seededRandom(9), ground: (x) => 2 + x * 0.01 });
  assert.equal(field.bolts.length, 6);
  for (let i = 0; i < 9; i++) {
    const hit = field.strike(0, 0);
    assert.ok(hit.distance >= 15 && hit.distance <= 70);
    assert.ok(Math.abs(hit.y - (2 + hit.x * 0.01)) < 1e-9, "a ground strike lands on the terrain height");
  }
  assert.equal(field.group.children.length, 6, "no new meshes are created per strike");
  const first = field.update(0.01);
  assert.ok(first.level > 0 && first.strike);
  let level = first.level;
  for (let i = 0; i < 80; i++) level = field.update(0.02).level;
  assert.equal(level, 0);
  assert.ok(field.bolts.every((b) => !b.mesh.visible));
  field.dispose();
});

function crownFixture(opts = {}) {
  const character = new T.Group();
  character.position.set(0, 0, 0);
  const world = new T.Scene();
  world.add(character);
  const crown = createEffectCrown(T, {
    character, world, ground: (x, z) => 0, rng: seededRandom(3), ...opts,
  });
  return { character, world, crown };
}

test("the crown is wide: coils sit well outside a cramped ~1 m helix", () => {
  const { crown } = crownFixture();
  const radii = crown.crown.children.map((coil) => {
    const p = coil.geometry.attributes.position;
    let sum = 0;
    for (let i = 0; i < p.count; i++) sum += Math.hypot(p.getX(i), p.getZ(i));
    return sum / p.count;
  });
  assert.equal(radii.length, DEFAULT_COILS.length);
  assert.ok(radii.every((r) => r > 2.2 && r < 4.3), `coils should be 2.4–3.8 m out, got ${radii.map((r) => r.toFixed(1))}`);
  // Fault: the original cramped coils fail the width expectation.
  const narrow = createEffectCrown(T, {
    character: new T.Group(), world: new T.Scene(), rng: seededRandom(1),
    coils: [{ radius: 0.9, turns: 4.5, low: -0.45, high: 3.75, spin: 1.65, tint: 0 }],
  });
  const p = narrow.crown.children[0].geometry.attributes.position;
  let sum = 0; for (let i = 0; i < p.count; i++) sum += Math.hypot(p.getX(i), p.getZ(i));
  assert.ok(sum / p.count < 2.2, "a ~1 m helix must not pass the wide-crown check");
});

test("hovering throws forks to a ring around the player; a burst fires every slot plus a shockwave", () => {
  const { crown } = crownFixture();
  crown.update({ active: true, intense: true }, 0.05);
  for (let i = 0; i < 20; i++) crown.update({ active: true, intense: true }, 0.05);
  const liveForks = crown.forks.filter((f) => f.mesh.visible);
  assert.ok(liveForks.length > 0, "forks strike while hovering");
  let farthest = 0;
  const pts = liveForks[0].mesh.geometry.attributes.position;
  for (let i = 0; i < pts.count; i++) if (pts.getY(i) < 0.05) farthest = Math.max(farthest, Math.hypot(pts.getX(i), pts.getZ(i)));
  assert.ok(farthest > 3.5 && farthest < 9.6, `landing on the 4–9 m ring, got ${farthest.toFixed(1)}`);
  crown.update({ active: true, burst: true }, 0.016);
  assert.equal(crown.forks.filter((f) => f.mesh.visible).length, crown.forks.length, "a burst fires every fork slot");
  assert.ok(crown.scorches.some((r) => r.userData.radius === 10 && r.visible), "a 10 m shockwave ring is emitted");
});

test("reduced motion holds a dim, still pose with no forks or scorches", () => {
  const { crown } = crownFixture();
  crown.update({ active: true, intense: true, reduced: true }, 0.05);
  const t0 = crown.crown.children[0].material.uniforms.time.value;
  crown.update({ active: true, intense: true, reduced: true }, 0.05);
  assert.equal(crown.crown.children[0].material.uniforms.time.value, t0, "the coils do not advance");
  assert.ok(crown.crown.children[0].material.uniforms.strength.value < 0.5, "coils are dimmed");
  assert.equal(crown.forks.filter((f) => f.mesh.visible).length, 0);
  assert.equal(crown.scorches.filter((r) => r.visible).length, 0);
  crown.dispose();
});

test("start mode: main game by default; tutorial for automation; save decides for returning players", () => {
  const q = (s = "") => new URLSearchParams(s);
  assert.equal(resolveStartMode({ params: q() }), "main");
  assert.equal(resolveStartMode({ params: q(), mainSave: '{"active":true}' }), "main");
  assert.equal(resolveStartMode({ params: q(), mainSave: '{"active":false}' }), "tutorial");
  assert.equal(resolveStartMode({ params: q(), mainSave: "{bad json" }), "main");
  assert.equal(resolveStartMode({ params: q("start=tutorial") }), "tutorial");
  assert.equal(resolveStartMode({ params: q("start=main"), webdriver: true }), "main");
  assert.equal(resolveStartMode({ params: q(), webdriver: true }), "tutorial");
  assert.equal(resolveStartMode({ params: q("start=player"), webdriver: true }), "main");
  assert.equal(resolveStartMode({ params: q("start=player"), webdriver: true, mainSave: '{"active":false}' }), "tutorial");
  // Custom mode names and query parameter.
  assert.equal(resolveStartMode({ params: q("mode=storm"), param: "mode", main: "storm", tutorial: "pass" }), "storm");
});
