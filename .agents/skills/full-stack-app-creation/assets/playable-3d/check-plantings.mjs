import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { validateRoots } from "./plantings.js";

export async function checkPlantings(browser, origin, evidence) {
  const names = JSON.parse(await readFile("public/plant-fixture/specimens.json", "utf8"));
  const checks = [];
  assert.throws(() => validateRoots([[4, -4]]), /raised deck/);
  checks.push("blocked footprint rejected");
  const url = new URL("?plantings", origin).href;
  const page = await browser.newPage({ viewport: { width: 880, height: 540 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  try {
    const transfers = Object.values(names).map(async ({ file, sha256 }) => {
      const response = await page.waitForResponse(response => response.url().endsWith("/" + file));
      assert(response.ok());
      assert.equal(createHash("sha256").update(await response.body()).digest("hex"), sha256);
    });
    assert((await page.goto(url)).ok());
    await Promise.all(transfers);
    checks.push("all three models served with the exported hashes");
    const ready = mode => page.waitForFunction(mode => {
      const layout = window.renderedCheckpoint?.plantings?.[mode];
      return layout?.visible && layout.entries.every(entry =>
        entry.state === "ready" && entry.sourceVisible && !entry.fallbackVisible);
    }, mode);
    await ready(0);
    const observe = () => page.evaluate(() => window.renderedCheckpoint.plantings);
    const modes = await observe();
    const entries = modes[0].entries;
    assert.equal(new Set(entries.map(entry => entry.variety)).size, 3);
    assert.equal(entries.filter(entry => entry.planting === "marker").length, 1);
    assert.equal(entries.filter(entry => entry.planting === "grove").length, 2);
    assert(entries.every(entry => entry.root[1] === 0));
    checks.push("one solitary specimen and a mixed pair stand on the floor");
    const full = entries.filter(entry => entry.detail === "full");
    assert.equal(full.length, 1);
    assert(entries.filter(entry => entry.detail === "canopy").every(entry => entry.drawn < full[0].drawn && entry.drawn > 0));
    checks.push("one full specimen and thinner authored canopies");
    await page.screenshot({ path: resolve(evidence, "planting-arrival.png") });
    const switcher = page.getByRole("button", { name: "Switch planting layout" });
    await switcher.click();
    await ready(1);
    assert.deepEqual((await observe()).map(mode => mode.visible), [false, true]);
    await page.screenshot({ path: resolve(evidence, "planting-second-layout.png") });
    await switcher.click();
    await ready(0);
    assert.deepEqual((await observe()).map(mode => mode.visible), [true, false]);
    checks.push("scene switch hides the previous grove and restores it on return");
    await page.keyboard.down("KeyS");
    try {
      await page.waitForFunction(() => window.renderedCheckpoint.plantings[0].entries
        .some(entry => entry.state === "ready" && entry.detail === "fallback" && entry.fallbackVisible && !entry.sourceVisible));
    } finally {
      await page.keyboard.up("KeyS");
    }
    checks.push("moving away swaps to a fallback silhouette");
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }

  const fault = await browser.newPage();
  const uncaught = [];
  fault.on("pageerror", error => uncaught.push(error.message));
  try {
    await fault.route("**/rounded.glb", route => route.fulfill({ status: 404, body: "" }));
    await fault.goto(url);
    await fault.waitForFunction(() => {
      const entries = window.renderedCheckpoint?.plantings?.[0].entries;
      return entries?.some(entry => entry.state === "fallback-error" && entry.fallbackVisible) &&
        entries?.some(entry => entry.state === "ready" && entry.sourceVisible);
    });
    const start = await fault.evaluate(() => window.renderedCheckpoint.z);
    await fault.keyboard.down("KeyW");
    await fault.waitForFunction(start => window.renderedCheckpoint.z < start - .1, start);
    await fault.keyboard.up("KeyW");
    await fault.screenshot({ path: resolve(evidence, "planting-unavailable.png") });
    assert.deepEqual(uncaught, []);
    checks.push("a missing GLB leaves its fallback, other trees and movement available");
  } finally {
    await fault.close();
  }
  return { mode: "authored-plantings", status: "pass", checks };
}
