// A scarf tail must stay outside the body while standing, sprinting with a forward lean
// and banking through turns. Faults reproduce the original clipping: a collider that does
// not follow the bone, and a fixed narrow capsule instead of the measured silhouette.
import test from "node:test";
import assert from "node:assert/strict";
import { frame, makeChain, makeProfile, pushOut, stepChain } from "./cloth-collider.mjs";

// Synthetic silhouette, heights relative to a chest pivot 1.05 m above the feet:
// [height, back, half-width, front]. A bulging cape below a narrow collar.
const ROWS = [
  [-1.0, .07, .16, .28], [-.6, .19, .26, .25], [-.15, .17, .34, .19], [0, .17, .37, .16],
  [.1, .23, .38, .16], [.25, .23, .38, .16], [.3, .2, .34, .14], [.35, .115, .11, .085], [.42, .1, .1, .08],
];
const PIVOT = 1.05, H = 1 / 120;
const truth = makeProfile(ROWS, 0);

function run({ followBone = true, rows = ROWS } = {}) {
  const profile = makeProfile(rows);
  const pos = { x: 0, y: 0, z: 0 };
  let yaw = 0, worst = 0, chain = null;
  for (let i = 0; i < 6 / H; i++) {
    const t = i * H, speed = t < 1.5 ? 0 : 7;
    const yawRate = t > 3.5 ? 2.5 * Math.sin(t * 1.3) : 0;
    yaw += yawRate * H;
    pos.x += Math.sin(yaw) * speed * H; pos.z += Math.cos(yaw) * speed * H;
    const lean = speed ? .3 : 0, bank = Math.max(-.26, Math.min(.26, -Math.atan(speed * yawRate / 9.81)));
    const bone = frame({ x: pos.x, y: PIVOT, z: pos.z }, yaw, lean, bank);
    const collider = followBone ? bone : frame({ x: pos.x, y: PIVOT, z: pos.z }, yaw, 0, 0);
    // The collar anchor, seated on the outside of the profile.
    const seat = { x: 0, y: .35, z: -.05 };
    pushOut(profile, seat);
    const root = bone.toWorld(seat);
    chain ??= makeChain(root, 1, 12);
    stepChain(chain, root, H, (p, q) => {
      const l = collider.toLocal(p);
      if (pushOut(profile, l, collider.toLocal(q))) Object.assign(p, collider.toWorld(l));
    });
    if (t > 1) {
      for (const p of chain.points.slice(1)) {
        const l = bone.toLocal(p), e = truth(l.y);
        if (!e) continue;
        const depth = l.z < 0 ? e.back : e.front, f = (l.x / e.side) ** 2 + (l.z / depth) ** 2;
        if (f < 1) worst = Math.max(worst, (1 - Math.sqrt(f)) * Math.min(e.side, depth));
      }
    }
  }
  return worst;
}

test("tails stay outside the measured body while standing, leaning, banking and turning", () => {
  const worst = run();
  assert.ok(worst < .01, `sank ${(worst * 100).toFixed(1)} cm`);
});

test("a fixed narrow capsule lets the tail sink into the cape (sensitivity)", () => {
  const narrow = ROWS.map(([y]) => [y, .1, .1, .08]);
  const worst = run({ rows: narrow });
  assert.ok(worst > .02, `narrow capsule only sank ${(worst * 100).toFixed(1)} cm`);
});

test("a collider that ignores lean and bank lets the tail sink (sensitivity)", () => {
  const worst = run({ followBone: false });
  assert.ok(worst > .02, `world-upright collider only ${(worst * 100).toFixed(1)} cm`);
});

test("tunnelling cloth exits on the side it came from", () => {
  const profile = makeProfile(ROWS);
  const p = { x: 0, y: .2, z: .05 };
  pushOut(profile, p, { x: .02, z: -.4 });
  assert.ok(p.z < -.2, "pushed back out behind, not through the chest");
});
