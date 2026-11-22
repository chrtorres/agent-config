// Whole-outfit cloth: a sleeve hem that hangs, droops and trails within its cone, and a
// long tied hair tail that must stay under a wide hat when the wearer stops from a sprint.
// The hat fault reproduces the originating defect: a ceiling that ended at the brim let
// the tail wrap round the edge and rise above the hat. All geometry here is synthetic.
import test from "node:test";
import assert from "node:assert/strict";
import { makeChain, stepChain } from "./cloth-collider.mjs";
import { HEM, clampUnderCeiling, hatCeiling, hemSwing, pullTowardRestLine, stepHem } from "./outfit-cloth.mjs";

const H = 1 / 120;

test("a sleeve hem hangs at rest, droops under a raised arm and stays in its cone", () => {
  const origin = { x: 0, y: 0, z: 0 }, down = { x: 0, y: -1, z: 0 }, length = .4;
  const state = { p: { x: 0, y: -length, z: 0 }, q: { x: 0, y: -length, z: 0 } };
  for (let i = 0; i < 240; i++) stepHem(state, { origin, rest: down, length, h: H });
  assert.ok(hemSwing(state, origin, down) < 1e-6, "no swing when hanging still");
  // Arm raised forward: the rest direction is horizontal; gravity droops the hem.
  const forward = { x: 0, y: 0, z: 1 };
  state.p = { x: 0, y: 0, z: length }; state.q = { ...state.p };
  for (let i = 0; i < 600; i++) stepHem(state, { origin, rest: forward, length, h: H });
  const droop = hemSwing(state, origin, forward);
  assert.ok(state.p.y < 0 && droop > .2 && droop <= HEM.cone + 1e-9, `droop ${droop.toFixed(3)} rad`);
});

test("a sleeve trails a moving pivot and settles after it stops", () => {
  const rest = { x: 0, y: -1, z: 0 }, length = .4, origin = { x: 0, y: 1, z: 0 };
  const state = { p: { x: 0, y: .6, z: 0 }, q: { x: 0, y: .6, z: 0 } };
  let trail = 0, settled = 1;
  for (let i = 0; i < 5 / H; i++) {
    const t = i * H, speed = t > 1 && t < 3 ? 7 : 0;
    origin.z += speed * H;
    stepHem(state, { origin, rest, length, h: H });
    if (t > 2 && t < 3) trail = Math.max(trail, hemSwing(state, origin, rest));
    if (t > 4.8) settled = Math.min(settled, hemSwing(state, origin, rest));
  }
  assert.ok(trail > .1 && trail <= HEM.cone + 1e-9, `trails ${trail.toFixed(3)} rad`);
  assert.ok(settled < .03, `settles to ${settled.toFixed(3)} rad`);
});

// Sprint, leap and land, then stop dead (the sequence that exposed the fault in game).
// Record the tail's highest point beyond the brim in the head frame from the leap on.
// Head pivot at the origin, tail anchored under the hat at the back of the crown.
function sprintStop({ ceilingReach, tie }) {
  const surface = (r) => .30 - .70 * r + .33 * r * r;        // conical straw hat underside
  const brim = .36, ceiling = hatCeiling(surface, brim, ceilingReach);
  const anchor = { x: 0, y: .16, z: -.12 };
  const back = { x: 0, y: -Math.cos(.3), z: -Math.sin(.3) };   // raked behind vertical
  const chain = makeChain(anchor, .64, 12);
  let z = 0, y = 0, vy = 0, highest = -Infinity;
  const local = (p) => ({ x: p.x, y: p.y - y, z: p.z - z });
  for (let i = 0; i < 4 / H; i++) {
    const t = i * H, speed = t > .5 && t < 2.5 ? 7 : 0;
    z += speed * H;                                             // the wearer runs along +z
    if (Math.abs(t - 1.8) < H / 2) vy = 5.5;                    // leap
    vy -= 9.81 * H; y = Math.max(0, y + vy * H); if (y === 0) vy = 0;
    const root = { x: anchor.x, y: anchor.y + y, z: anchor.z + z };
    stepChain(chain, root, H, () => {});
    if (tie) pullTowardRestLine(chain, root, back, 16, H);
    // The hat lives in the head frame: clamp there, then return to world space.
    for (const p of chain.points) {
      const l = local(p);
      clampUnderCeiling([l], ceiling);
      p.y = l.y + y;
      if (t > 1.8 && Math.hypot(l.x, l.z) > brim) highest = Math.max(highest, l.y);
    }
  }
  return { highest, brimHeight: surface(brim) };
}

test("a hat ceiling that ends at the brim lets a stopped tail rise above the hat", () => {
  const { highest, brimHeight } = sprintStop({ ceilingReach: .36, tie: false });
  assert.ok(highest > brimHeight + .05, `fault reproduced: ${(highest - brimHeight).toFixed(3)} m above the brim`);
});

test("an extended ceiling and a tie keep the tail under the brim", () => {
  const { highest, brimHeight } = sprintStop({ ceilingReach: 1.2, tie: true });
  assert.ok(highest <= brimHeight + 1e-9, `highest point ${(highest - brimHeight).toFixed(3)} m vs brim`);
});
