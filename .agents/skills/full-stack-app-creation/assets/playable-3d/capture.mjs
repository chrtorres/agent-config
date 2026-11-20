import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

export async function capturePresentation(browser, origin, directory, ultra) {
  await mkdir(directory);
  const width = ultra ? 3840 : 960;
  const height = ultra ? 2160 : 540;
  const fps = 24;
  const count = fps * 2;
  const shots = [];
  for (const fallback of [false, true]) {
    const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    try {
      await page.addInitScript(fallback => {
        if (fallback) {
          const extension = WebGL2RenderingContext.prototype.getExtension;
          WebGL2RenderingContext.prototype.getExtension = function (name) {
            return name === "EXT_color_buffer_float" ? null : extension.call(this, name);
          };
        }
        let callbacks = [], ticks = 0;
        const pad = { connected: true, index: 0, mapping: "standard", axes: [0, 0], buttons: [] };
        Object.defineProperty(navigator, "getGamepads", { value: () => [pad] });
        window.requestAnimationFrame = callback => callbacks.push(callback);
        window.captureFrame = (fps, axis, capture) => {
          pad.axes[1] = axis;
          const scheduled = callbacks;
          callbacks = [];
          for (const callback of scheduled) callback(ticks * 1000 / fps);
          ticks++;
          const canvas = document.querySelector("canvas");
          const gl = canvas.getContext("webgl2");
          const debug = gl.getExtension("WEBGL_debug_renderer_info");
          return {
            state: window.renderedCheckpoint,
            device: gl.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
            size: [gl.drawingBufferWidth, gl.drawingBufferHeight],
            png: capture ? canvas.toDataURL("image/png") : null,
          };
        };
      }, fallback);
      assert.equal((await page.goto(new URL("?quality=ultra-4k", origin).href)).status(), 200);
      await page.locator("canvas").waitFor();
      const step = (axis, capture = false) =>
        page.evaluate(({ fps, axis, capture }) => window.captureFrame(fps, axis, capture), { fps, axis, capture });
      const uhd = await step(0, true);
      assert.deepEqual(uhd.size, [3840, 2160]);
      assert.equal(uhd.state.resolution.antiAlias, fallback ? "native" : "fxaa");
      assert.equal(uhd.state.resolution.postWidth, fallback ? 0 : 3840);
      await writeFile(resolve(directory, fallback ? "fallback-uhd.png" : "cinematic-uhd.png"), decode(uhd.png));
      await page.locator("#quality").click();
      const balanced = await step(0);
      assert.deepEqual(balanced.size, [960, 540]);
      assert.equal(balanced.state.resolution.postWidth, 0);
      shots.push({ fallback, device: uhd.device, uhd: uhd.state.resolution, balanced: balanced.state.resolution });
      if (!fallback) {
        await page.locator("#quality").click();
        if (ultra) await page.locator("#quality").click();
        const trace = [];
        for (let i = 0; i < count; i++) {
          const { size, png, state } = await step(-Math.min(1, i / 12), true);
          assert.deepEqual(size, [width, height]);
          assert.equal(state.resolution.antiAlias, "fxaa");
          await writeFile(resolve(directory, `frame-${String(i).padStart(4, "0")}.png`), decode(png));
          trace.push({ frame: state.frames, z: state.z, boots: state.boots });
        }
        assert.equal(trace.at(-1).frame - trace[0].frame, count - 1);
        assert(trace[0].z - trace.at(-1).z > 1);
        shots.at(-1).trace = trace;
      }
      assert.deepEqual(errors, []);
    } finally {
      await page.close();
    }
  }
  const manifest = { width, height, fps, count, shots };
  await writeFile(resolve(directory, "timeline.json"), JSON.stringify(manifest, null, 2));
  return { mode: "cinematic-capture", status: "pass", width, height, fps, count };
}

function decode(png) {
  assert(png.startsWith("data:image/png;base64,"));
  return Buffer.from(png.slice("data:image/png;base64,".length), "base64");
}
