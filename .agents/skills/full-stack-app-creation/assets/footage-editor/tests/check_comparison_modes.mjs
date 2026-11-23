import assert from "node:assert/strict";
import {join} from "node:path";
import {pathToFileURL} from "node:url";

const [url, playwright, executablePath, fixtures] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(join(playwright, "index.mjs")));
const browser = await chromium.launch({executablePath});
try {
  const page = await browser.newPage();
  await page.goto(url);
  await page.locator("#face-swap > summary").click();
  await page.locator("#upload-file").setInputFiles(join(fixtures, "target.png"));
  await page.locator("#face-portrait").setInputFiles(join(fixtures, "source.png"));
  await page.waitForFunction(() => document.querySelector("#face-target-image").naturalWidth);
  await page.locator("#face-target-picker").press("Enter");
  await page.locator("#face-run").click();
  await page.locator("#face-stage-display").click({timeout:120000});
  await page.waitForFunction(() => document.querySelector(".quick-frame > #face-image-result")?.naturalWidth
    && document.querySelector("#face-monitor").getContext("2d").getImageData(1, 1, 1, 1).data[3] === 255);
  await page.locator("#face-display").click();
  assert.ok(await page.locator("#quick-image").isVisible());
  await page.locator("#face-clear").click();
  await page.locator("#face-result").waitFor({state:"hidden"});

  // Isolate restored presentation state from the separate pose-preparation pipeline.
  await page.route(url, route => route.fulfill({path:"app/index.html", contentType:"text/html"}));
  await page.route("**/events", route => route.abort());
  await page.route("**/face-swap/status", route => route.fulfill({json:{
    phase:"ready", report:{prepared_target:true, swapped:9, frames:12}
  }}));
  await page.route("**/face-swap/preview.mp4", route => route.fulfill({
    path:join(fixtures, "target.mp4"), contentType:"video/mp4"
  }));
  await page.reload();
  await page.locator("#face-stage-display").click();
  await page.waitForFunction(() => document.querySelector("#stage-viewport > #face-video")?.readyState >= 2);
  await page.locator("#tab-face").click();
  assert.ok(await page.locator("#face-monitor").isVisible());
  await page.locator("#face-display").click();
  assert.ok(await page.locator("#stage-content").isVisible());
} finally {
  await browser.close();
}
