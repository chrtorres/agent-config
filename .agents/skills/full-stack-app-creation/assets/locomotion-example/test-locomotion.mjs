// Real-world locomotion baseline: each bound is derived from a physical formula, and the
// smoothness check is proven sensitive by re-running it with the smoothing disabled.
import test from "node:test";
import assert from "node:assert/strict";
import {
  BODY, LOCOMOTION, dragFactor, jumpReach, landingRetention, pushOff, steerFacing, stepLocomotion,
} from "./locomotion.mjs";

const DT = 1 / 240;
const near = (a, b, tol) => Math.abs(a - b) <= tol;

test("jump takeoffs give measured rises and the footage flight time", () => {
  assert.ok(near(BODY.jump ** 2 / (2 * BODY.g), .37, .01), "standing countermovement jump");
  assert.ok(near(BODY.leap ** 2 / (2 * BODY.g), .555, .01), "running leap");
  // Example footage measurement: 20 frames of flight at 29.97 fps.
  assert.ok(near(2 * BODY.leap / BODY.g, 20 / 29.97, .015));
});

test("sprint from rest follows the force-velocity curve", () => {
  const v = { x: 0, z: 0 };
  let t = 0, d = 0, peak = 0;
  while (d < 30) {
    stepLocomotion(v, { dirX: 0, dirZ: 1, maxSpeed: BODY.sprint, grounded: true, dt: DT });
    t += DT; d += v.z * DT; peak = Math.max(peak, v.z);
  }
  assert.ok(t > 4.3 && t < 5.3, `30 m in ${t.toFixed(2)} s`);
  assert.ok(peak <= BODY.sprint * 1.01, `peak ${peak}`);
});

test("stopping distance is v²/2a plus the force-rise lag; reversal is friction-limited", () => {
  const v = { x: 0, z: BODY.sprint };
  let d = 0;
  while (v.z > 0) { stepLocomotion(v, { dirX: 0, dirZ: 0, maxSpeed: BODY.sprint, grounded: true, dt: DT }); d += v.z * DT; }
  const expected = BODY.sprint ** 2 / (2 * BODY.stop) + BODY.sprint * LOCOMOTION.forceRise;
  assert.ok(near(d, expected, .15), `${d.toFixed(2)} m, expected ${expected.toFixed(2)}`);
  const rev = { x: 0, z: BODY.sprint };
  stepLocomotion(rev, { dirX: 0, dirZ: -1, maxSpeed: BODY.sprint, grounded: true, dt: .1 });
  assert.ok(BODY.sprint - rev.z <= BODY.mu * BODY.g * .1 + 1e-9);
});

test("flight is ballistic: no steering, drag only, plausible terminal velocity", () => {
  const v = { x: 0, z: BODY.sprint };
  stepLocomotion(v, { dirX: 1, dirZ: 0, maxSpeed: BODY.sprint, grounded: false, dt: .1 });
  assert.equal(v.x, 0);
  let vy = 0;
  for (let i = 0; i < 60 / DT; i++) { vy -= BODY.g * DT; vy *= dragFactor(Math.abs(vy), DT); }
  assert.ok(vy < -44 && vy > -56, `terminal ${vy.toFixed(1)} m/s`);
});

test("takeoff and landing: broad-jump push, sprint leap ≈ 5 m, 2 m drop is hard", () => {
  assert.ok(near(pushOff({ x: 0, z: 0 }, 0, 1).z, BODY.push, 1e-9));
  assert.equal(pushOff({ x: 0, z: 7 }, 0, 1).z, 7, "legs cannot add speed to a sprint");
  assert.ok(near(jumpReach(BODY.sprint, BODY.leap), 5.05, .05));
  assert.equal(landingRetention(-Math.sqrt(2 * BODY.g * .5)), 1);
  assert.ok(landingRetention(-Math.sqrt(2 * BODY.g * 3)) < .9);
});

// Seven stick patterns; returns the worst jerk, horizontal force and per-frame facing step.
function turnMetrics(tuning = LOCOMOTION) {
  const dt = 1 / 60, dir = (a, m = 1) => ({ x: Math.sin(a) * m, z: Math.cos(a) * m });
  const scenarios = {
    "run 90° cut": [BODY.run, (t) => dir(t < 1 ? 0 : Math.PI / 2)],
    "sprint 90° cut": [BODY.sprint, (t) => dir(t < 2.5 ? 0 : Math.PI / 2)],
    "run 135° turn": [BODY.run, (t) => dir(t < 1 ? 0 : 2.36)],
    "run 180° reverse": [BODY.run, (t) => dir(t < 1 ? 0 : Math.PI)],
    "walk 90° cut": [BODY.run, (t) => dir(t < 1 ? 0 : Math.PI / 2, .45)],
    "sprint slalom": [BODY.sprint, (t) => dir(t < 2.5 ? 0 : Math.sin((t - 2.5) * 4.4) * 1.05)],
    "stick sweep": [BODY.run, (t) => dir(t < 1 ? 0 : (t - 1) * 2.5)],
  };
  const out = {};
  for (const [name, [max, stick]] of Object.entries(scenarios)) {
    const v = { x: 0, z: 0 };
    let facing = 0, prevA = null, jerk = 0, force = 0, snap = 0;
    for (let t = 0; t < 5; t += dt) {
      const d = stick(t), before = { ...v };
      stepLocomotion(v, { dirX: d.x, dirZ: d.z, maxSpeed: max, grounded: true, dt }, tuning);
      const a = { x: (v.x - before.x) / dt, z: (v.z - before.z) / dt };
      force = Math.max(force, Math.hypot(a.x, a.z));
      if (prevA) jerk = Math.max(jerk, Math.hypot(a.x - prevA.x, a.z - prevA.z) / dt);
      prevA = a;
      const want = Math.hypot(v.x, v.z) > .8 ? Math.atan2(v.x, v.z) : Math.atan2(d.x, d.z);
      const next = steerFacing(facing, want, dt, tuning);
      snap = Math.max(snap, Math.abs(Math.atan2(Math.sin(next - facing), Math.cos(next - facing))));
      facing = next;
    }
    out[name] = { jerk, force, snap };
  }
  return out;
}

const smooth = ({ jerk, force, snap }, dt = 1 / 60) =>
  jerk < 150 && force <= BODY.mu * BODY.g + 1e-6 && snap <= LOCOMOTION.pivotRate * dt + 1e-9;

test("turn transitions: bounded jerk, friction circle, pivot-limited facing", () => {
  for (const [name, m] of Object.entries(turnMetrics())) {
    assert.ok(smooth(m), `${name}: ${JSON.stringify(m)}`);
  }
});

test("the smoothness check rejects instant force and instant facing (sensitivity)", () => {
  const noRise = turnMetrics({ ...LOCOMOTION, forceRise: 0 });
  assert.ok(Object.values(noRise).some((m) => !smooth(m)), "force switching within a frame must fail");
  const noPivot = turnMetrics({ ...LOCOMOTION, pivotRate: Infinity });
  assert.ok(Object.values(noPivot).some((m) => !smooth(m)), "an instant facing flip must fail");
});

test("level design check: a gap is a jump only when the physics can clear it", () => {
  // Spacing obstacles from jumpReach keeps a course traversable at the real baseline.
  const rise = .3, gap = 2; // standing reach ≈ 1.0 m, 4 m/s run-up ≈ 2.3 m
  assert.ok(jumpReach(BODY.push, BODY.jump, rise) < gap, "standing jump falls short");
  assert.ok(jumpReach(4, BODY.leap, rise) > gap, "a short run-up clears it");
  assert.equal(jumpReach(BODY.sprint, BODY.leap, .6), null, "a 0.6 m rise is a climb, not a jump");
});
