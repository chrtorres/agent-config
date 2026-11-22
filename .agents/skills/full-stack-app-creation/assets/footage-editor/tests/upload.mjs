import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {pathToFileURL} from "node:url";

const [url, playwright, executablePath, fixture, dimensions] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(join(playwright, "index.mjs")));
const browser = await chromium.launch({executablePath, args: ["--no-sandbox", "--enable-unsafe-swiftshader"]});
try {
  const context = await browser.newContext({viewport: {width: 390, height: 740}});
  const page = await context.newPage();
  await page.goto(url);
  await page.getByRole("heading", {name: "Open video or image"}).waitFor();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.equal((await page.request.get(new URL("/source.mp4", url).href)).status(), 404);

  const upload = page.getByRole("button", {name: "Upload and prepare"});
  const picker = page.getByLabel("Video or image file");
  const waitForPreparedEditor = async () => {
    try {
      const outcome = await Promise.race([
        page.getByRole("heading", {name: "Footage motion review"}).waitFor({timeout: 180_000}).then(() => null),
        page.locator("#upload-status").filter({hasText: /could not|failed|unable|timed out|wasn’t visible|temporary storage/i})
          .waitFor({timeout: 180_000}).then(() => page.locator("#upload-status").textContent()),
      ]);
      if (outcome) throw new Error(outcome);
    } catch (error) {
      throw new Error(`Upload did not open the motion editor. ${error.message}`, {cause: error});
    }
  };
  await picker.setInputFiles({name: "invalid.mp4", mimeType: "video/mp4", buffer: Buffer.from("invalid")});
  await upload.click();
  await page.getByText("Choose an MP4 video with H.264 video and AAC or no audio. Other formats are not converted.").waitFor();
  assert.equal(await upload.isEnabled(), true);

  const foreign = await page.request.post(new URL("/upload", url).href, {
    data: Buffer.from("invalid"),
    headers: {"Origin": "https://example.com", "Content-Type": "application/octet-stream"},
  });
  assert.equal(foreign.status(), 403);

  await picker.setInputFiles(fixture);
  await upload.click();
  await page.locator("#upload-job").waitFor();
  assert.equal(await picker.isDisabled(), true);
  await waitForPreparedEditor();
  await page.locator("#loading").waitFor({state: "hidden"});
  await page.getByRole("button", {name: "Play video"}).click();
  await page.waitForFunction(() => document.querySelector("#source").currentTime > .05);
  await page.getByRole("button", {name: "Pause video"}).click();
  const native = await page.locator("#screen").evaluate(canvas => [canvas.width, canvas.height]);
  if (dimensions) assert.deepEqual(native, dimensions.split("x").map(Number));
  const display = page.getByLabel("Display");
  const bounds = () => page.evaluate(() => {
    const frame = document.getElementById("stage-viewport");
    const canvas = document.getElementById("screen");
    return [frame.clientWidth, frame.clientHeight, canvas.clientWidth, canvas.clientHeight];
  });
  const [fw, fh, cw, ch] = await bounds();
  assert.ok(cw <= fw + 1 && ch <= fh + 1);
  await display.selectOption("fill");
  const [fillWidth, fillHeight, mediaWidth, mediaHeight] = await bounds();
  assert.ok(mediaWidth >= fillWidth - 1 && mediaHeight >= fillHeight - 1);
  await display.selectOption("center");
  const [centerWidth, centerHeight, centeredWidth, centeredHeight] = await bounds();
  const centerScale = Math.min(1, centerWidth / native[0], centerHeight / native[1]);
  assert.deepEqual([centeredWidth, centeredHeight], native.map(side => Math.round(side * centerScale)));
  await display.selectOption("stretch");
  const [stretchWidth, stretchHeight, stretchedWidth, stretchedHeight] = await bounds();
  assert.deepEqual([stretchedWidth, stretchedHeight], [stretchWidth, stretchHeight]);
  await display.selectOption("fit");
  const source = await page.request.get(new URL("/source.mp4", url).href);
  assert.equal(source.status(), 200);
  assert.deepEqual(await source.body(), await readFile(fixture));
  const foreignHost = await page.request.get(new URL("/source.mp4", url).href, {
    headers: {"Host": "example.com"},
  });
  assert.equal(foreignHost.status(), 403);
  const range = await page.request.get(new URL("/video.mp4", url).href, {headers: {Range: "bytes=0-63"}});
  assert.equal(range.status(), 206);
  assert.equal((await range.body()).length, 64);

  await page.getByRole("link", {name: "Use 4K controls"}).click();
  await page.locator("#loading").waitFor({state: "hidden"});
  const uhd = await page.locator("#screen").evaluate(canvas => [canvas.width, canvas.height]);
  assert.deepEqual(uhd, native.map(side => Math.max(2, 2 * Math.round(side * 1920 / Math.max(...native)))));
  const edit = page.getByRole("tab", {name: "Edit"});
  await edit.focus();
  await edit.press("ArrowRight");
  assert.equal(await page.getByRole("tab", {name: "Motion"}).getAttribute("aria-selected"), "true");
  assert.equal(await page.getByRole("region", {name: "Movement controls"}).isVisible(), true);
  await page.getByLabel("Theme").selectOption("light");
  assert.equal(await page.locator("html").getAttribute("data-theme"), "light");
  await page.getByLabel("Theme").selectOption("dark");
  const secondTab = await context.newPage();
  await secondTab.goto(new URL("/4k/", url).href);
  assert.equal(await secondTab.getByLabel("Theme").inputValue(), "dark");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", {name: "Clear video"}).click();
  await page.getByRole("heading", {name: "Open video or image"}).waitFor();
  await secondTab.getByRole("heading", {name: "Open video or image"}).waitFor();
  for (const path of ["/source.mp4", "/video.mp4", "/4k.mp4", "/regions.json", "/timeline/timeline.json"]) {
    assert.equal((await page.request.head(new URL(path, url).href)).status(), 404);
  }
  assert.equal(await page.getByLabel("Theme").inputValue(), "dark");
  await page.getByLabel("Video or image file").setInputFiles(fixture);
  await page.getByRole("button", {name: "Upload and prepare"}).click();
  await waitForPreparedEditor();
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", {name: "Clear video"}).click();
  await page.getByRole("heading", {name: "Open video or image"}).waitFor();
  console.log(`Browser upload, playback, native ${native.join("×")}, 4K ${uhd.join("×")}, keyboard tabs, theme and clear passed.`);
} finally {
  await browser.close();
}
