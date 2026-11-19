import assert from "node:assert/strict";
import { test } from "node:test";
import { createGame, frameDelta, restore, STEP } from "./core.js";

test("startup, background gaps and out of order timestamps are bounded", () => {
  assert.equal(frameDelta(100, null), 0);
  assert.equal(frameDelta(100, 120), 0);
  assert.equal(frameDelta(1000, 0), .05);
});
test("checkpoint input survives a substep and writes just once", () => {
  let raw, writes = 0;
  const storage = { getItem: () => raw, setItem: (_, value) => { raw = value; writes++; } };
  const game = createGame(storage);
  for (let i = 0; i < 15; i++) game.update(.05, { z: -1 });
  assert.equal(game.update(STEP / 2, { interact: true }).reached, false);
  assert.equal(game.update(.05).reached, true);
  assert.equal(writes, 1);
  assert.equal(restore(storage).reached, true);
});
test("invalid saves recover and storage denial is observable", () => {
  const storage = { getItem: () => "{broken", setItem: () => { throw Error("Denied"); } };
  const game = createGame(storage);
  assert.equal(game.update(0).z, 0);
  for (let i = 0; i < 15; i++) game.update(.05, { z: -1 });
  assert.equal(game.update(.05, { interact: true }).saveError, true);
});
