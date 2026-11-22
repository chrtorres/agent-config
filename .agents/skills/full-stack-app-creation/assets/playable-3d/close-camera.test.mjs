import test from "node:test";
import assert from "node:assert/strict";
import { orbitAround, redirectRender } from "./close-camera.mjs";

const vec = () => ({ x: 0, y: 0, z: 0, set(x, y, z) { Object.assign(this, { x, y, z }); return this; } });
const camera = (name) => ({ name, position: vec(), target: null, lookAt(x, y, z) { this.target = { x, y, z }; } });

test("only the game camera's renders are redirected, and restore puts the original back", () => {
  const calls = [];
  const renderer = { render(scene, cam) { calls.push(cam.name); } };
  const original = renderer.render;
  const main = camera("main"), inspect = camera("inspect"), shadow = camera("shadow");
  let placed = 0;
  const restore = redirectRender(renderer, main, inspect, () => placed++);
  renderer.render({}, main);
  renderer.render({}, shadow);
  assert.deepEqual(calls, ["inspect", "shadow"]);
  assert.equal(placed, 1, "placed once per redirected frame");
  restore();
  assert.equal(renderer.render, original);
  renderer.render({}, main);
  assert.equal(calls.at(-1), "main");
});

test("orbitAround follows the player's position and facing", () => {
  const player = { position: { x: 10, y: 2, z: -3 }, rotation: { y: Math.PI / 2 } };
  const cam = camera("inspect");
  orbitAround(player, { yaw: 0, distance: 3, height: 1.5, focus: 1 })(cam);
  // Facing +X (yaw PI/2), yaw 0 puts the camera in front: +3 m along X.
  assert.ok(Math.abs(cam.position.x - 13) < 1e-9 && Math.abs(cam.position.z + 3) < 1e-9);
  assert.equal(cam.position.y, 3.5);
  assert.deepEqual(cam.target, { x: 10, y: 3, z: -3 });
});
