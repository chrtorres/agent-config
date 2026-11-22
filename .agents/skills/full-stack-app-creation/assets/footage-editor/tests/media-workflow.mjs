import assert from "node:assert/strict";
import {readdir, readFile} from "node:fs/promises";
import {join} from "node:path";
import {pathToFileURL} from "node:url";

const [url, playwright, executablePath, fixtures] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(join(playwright, "index.mjs")));
const browser = await chromium.launch({executablePath, downloadsPath:fixtures,
  args:["--no-sandbox","--enable-unsafe-swiftshader"]});
const report = {images:[], videos:[], errors:[]};
try {
  const page = await browser.newPage({acceptDownloads:true});
  page.on("dialog", dialog => dialog.accept());
  await page.goto(url);
  const file = page.getByLabel("Video or image file");
  async function download(button, destination) {
    const requested = page.waitForEvent("download", {timeout:60000});
    await button.click();
    await (await requested).saveAs(destination);
    const bytes = await readFile(destination);
    assert.ok(bytes.length > 128, "Download contains media");
    return bytes;
  }
  async function brighten() {
    const slider = page.getByLabel("Brightness", {exact:true});
    if (!(await slider.isVisible())) await page.getByText("Adjust preview", {exact:true}).click();
    await slider.fill("115");
  }
  const names = (await readdir(fixtures)).filter(name => !name.startsWith("output-"));
  for (const name of names.filter(name => /\.(png|jpg|webp)$/.test(name))) {
    try {
      await file.setInputFiles(join(fixtures,name));
      await page.waitForFunction(() => document.querySelector("#quick-image").naturalWidth > 0);
      await brighten();
      const png = await download(page.getByRole("button", {name:"Download edited media"}),join(fixtures,"output-"+name+".png"));
      assert.equal(png.subarray(1,4).toString(),"PNG");
      await page.getByRole("button", {name:"Clear selection"}).click();
      report.images.push(name);
    } catch (error) {
      report.errors.push(name+": "+error.message.split("\n")[0]);
      await page.reload();
    }
  }
  for (const name of names.filter(name => /\.(mov|webm|mkv|avi)$/.test(name))) {
    try {
      // Other containers are rejected with guidance instead of being converted.
      await file.setInputFiles(join(fixtures,name));
      await page.getByRole("button", {name:"Upload and prepare"}).click();
      await page.locator("#upload-status").filter({hasText:/MP4/}).waitFor({timeout:30000});
      await page.getByRole("button", {name:"Clear selection"}).click();
      report.rejected = [...(report.rejected ?? []), name];
    } catch (error) {
      report.errors.push(name+": "+error.message.split("\n")[0]);
      await page.goto(url);
    }
  }
  for (const name of names.filter(name => /\.mp4$/.test(name))) {
    try {
      const path = join(fixtures,name);
      await file.setInputFiles(path);
      await page.getByRole("button", {name:"Upload and prepare"}).click();
      try {
        await page.getByRole("heading", {name:"Footage motion review"}).waitFor({timeout:180000});
      } catch (error) {
        throw new Error(await page.locator("#upload-status").textContent() || error.message);
      }
      await page.locator("#loading").waitFor({state:"hidden"});
      assert.equal(await page.locator("#error").isHidden(),true);
      await page.getByRole("button",{name:"Play video"}).click();
      await page.waitForFunction(() => document.querySelector("#source").currentTime > .05);
      await page.getByRole("button",{name:"Pause video"}).click();
      assert.deepEqual(await (await page.request.get(new URL("/source.mp4",url).href)).body(),await readFile(path));
      assert.equal((await page.request.head(new URL("/4k.mp4",url).href)).status(),404);
      if (name === "mp4.mp4" || name === "rotated.mp4") {
        await page.locator("#tone-panel summary").click();
        await page.locator("#tone-light").fill("22");
        const mp4 = await download(page.getByRole("button", {name:"Download shape and color edits"}),
          join(fixtures,"output-prepared-"+name.split(".")[0]+".mp4"));
        assert.equal(mp4.subarray(4,8).toString(),"ftyp");
        const frame = await download(page.getByRole("button",{name:"Download current frame"}),
          join(fixtures,"output-frame-"+name+".png"));
        assert.equal(frame.subarray(1,4).toString(),"PNG");
        if (name === "mp4.mp4" && process.env.FOOTAGE_EXPECT_UHD_FAILURE) {
          await page.getByRole("link",{name:"Watch in 4K"}).click();
          await page.getByRole("button",{name:"Retry 4K"}).waitFor();
          assert.equal((await page.request.head(new URL("/4k.mp4",url).href)).status(),404);
          const native = await page.request.head(new URL("/video.mp4",url).href);
          assert.equal(native.status(),200,"Native playback survives a failed 4K render");
          await page.getByRole("button",{name:"Retry 4K"}).click();
          await page.getByRole("link",{name:"Download 4K"}).waitFor({timeout:90000});
          assert.equal((await page.request.head(new URL("/4k.mp4",url).href)).status(),200);
        }
      }
      await page.getByRole("button",{name:"Clear video"}).click();
      await page.getByRole("heading",{name:"Open video or image"}).waitFor();
      if (name === "silent.mp4") {
        await file.setInputFiles(path);
        await brighten();
        const mp4 = await download(page.getByRole("button",{name:"Download edited media"}),
          join(fixtures,"output-quick.mp4"));
        assert.equal(mp4.subarray(4,8).toString(),"ftyp");
        await page.getByRole("button",{name:"Clear selection"}).click();
      }
      report.videos.push(name);
    } catch (error) {
      report.errors.push(name+": "+error.message.split("\n")[0]);
      const clear = page.getByRole("button",{name:"Clear video"});
      if (await clear.isVisible()) await clear.click();
      await page.goto(url);
    }
  }
} finally {
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
}
assert.equal(report.errors.length,0);
