import assert from "node:assert/strict";
import { mkdir, realpath, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { chromium } from "playwright";
import { preview } from "vite";
import { checkPoseReplay } from "./replay-pose.mjs";

const output = process.argv[2];
assert(output, "Usage: npm run smoke -- <evidence-directory-outside-app>");
await mkdir(output, { recursive: true });
const evidence = await realpath(output);
const boundary = relative(await realpath("."), evidence);
assert(boundary === ".." || boundary.startsWith(".." + sep) || isAbsolute(boundary));
const options = process.env.BROWSER_GPU === "1"
  ? ["--use-gl=angle", "--use-angle=gl"]
  : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
const server = await preview({ configFile: false, preview: { host: "127.0.0.1", port: 0, strictPort: true } });
let browser;
const results = { backend: process.env.BROWSER_GPU === "1" ? "ANGLE GL requested" : "SwiftShader requested", cases: [] };
const url = new URL("http://127.0.0.1");
url.port = server.httpServer.address().port;
try {
  browser = await chromium.launch({ args: options });
  for (const mode of ["keyboard", "synthetic-controller", "storage-denied"]) {
    const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    await page.addInitScript(mode => {
      // Keep physical devices from changing the input stream of an isolated fixture.
      Object.defineProperty(navigator, "getGamepads", { value: () => window.fixturePad ? [null, window.fixturePad] : [] });
      if (mode === "storage-denied") Storage.prototype.setItem = () => { throw new DOMException("Denied", "SecurityError"); };
    }, mode);
    assert.equal((await page.goto(url.href)).status(), 200);
    await page.waitForFunction(() => window.renderedCheckpoint?.frames > 1);
    if (mode === "synthetic-controller") {
      await page.evaluate(() => { window.fixturePad = { connected: true, mapping: "standard", index: 1, axes: [0, -1], buttons: [{ pressed: false }] }; });
    } else await page.keyboard.down("KeyW");
    await page.waitForFunction(() => window.renderedCheckpoint.z < -2.65);
    if (mode === "synthetic-controller") {
      await page.evaluate(() => { window.fixturePad.axes[1] = 0; window.fixturePad.buttons[0].pressed = true; });
    } else {
      await page.keyboard.up("KeyW");
      await page.keyboard.press("KeyE");
    }
    await page.waitForFunction(() => window.renderedCheckpoint.reached && window.renderedCheckpoint.cameraDistance > 3);
    assert.equal(await page.locator("#status").textContent(), mode === "storage-denied" ? "Save unavailable" : "Checkpoint saved");
    await page.screenshot({ path: resolve(evidence, mode + ".png") });
    await page.reload();
    await page.waitForFunction(() => window.renderedCheckpoint?.frames > 1);
    assert.equal(await page.evaluate(() => window.renderedCheckpoint.reached), mode !== "storage-denied");
    assert.deepEqual(errors, []);
    results.cases.push({ mode, status: "pass", consoleErrors: errors });
    await page.close();
  }
  for (const hz of [20, 60]) results.cases.push(await checkPoseReplay(browser, url.href, hz));
} catch (error) {
  results.failure = error.message;
  throw error;
} finally {
  await browser?.close();
  await new Promise((done, reject) => server.httpServer.close(error => error ? reject(error) : done()));
  await writeFile(resolve(evidence, "results.json"), JSON.stringify(results, null, 2));
}
