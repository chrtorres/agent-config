import assert from "node:assert/strict";

export async function checkPoseReplay(browser, url, hz) {
  async function trace(interrupt) {
    const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    try {
      await page.addInitScript(() => {
        let callbacks = [], now = 0;
        const pad = { connected: true, mapping: "standard", index: 0, axes: [0, 0], buttons: [] };
        Object.defineProperty(navigator, "getGamepads", { value: () => [pad] });
        window.requestAnimationFrame = callback => callbacks.push(callback);
        window.fixtureTick = (ms, axis) => {
          pad.axes[1] = axis;
          now += ms;
          const scheduled = callbacks;
          callbacks = [];
          for (const callback of scheduled) callback(now);
          return window.renderedCheckpoint;
        };
      });
      assert.equal((await page.goto(url)).status(), 200);
      await page.waitForFunction(() => typeof window.fixtureTick === "function");
      const samples = await page.evaluate(({ hz, interrupt }) => {
        const sample = axis => window.fixtureTick(1000 / hz, axis);
        sample(0);
        let before;
        for (let i = 0; i < Math.ceil(hz * .5); i++) before = sample(-1);
        const neutral = interrupt ? sample(0) : null;
        return { before, neutral, after: [sample(-1), sample(-1), sample(-1)] };
      }, { hz, interrupt });
      assert.deepEqual(errors, []);
      return samples;
    } finally {
      await page.close();
    }
  }
  const continuous = await trace(false);
  const interrupted = await trace(true);
  assert.equal(interrupted.neutral.frames, interrupted.before.frames + 1);
  assert.deepEqual(interrupted.neutral.boots, interrupted.before.boots, "Neutral-frame pose must hold");
  assert.notDeepEqual(continuous.after[0].boots, continuous.before.boots, "Continuous reference must move");
  for (const [i, frame] of interrupted.after.entries()) {
    assert.equal(frame.frames, interrupted.neutral.frames + i + 1);
    assert.deepEqual(frame.boots, continuous.after[i].boots, "Resume must match the uninterrupted step");
  }
  return { mode: "synthetic-pose-replay", hz, status: "pass", continuous, interrupted };
}
