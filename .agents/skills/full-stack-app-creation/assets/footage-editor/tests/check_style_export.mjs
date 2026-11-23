import assert from "node:assert/strict";
import {join} from "node:path";
import {pathToFileURL} from "node:url";
import {writeFile} from "node:fs/promises";

const [url, playwright, executablePath, output] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(join(playwright, "index.mjs")));
const browser = await chromium.launch({executablePath});
try {
  const page = await browser.newPage({acceptDownloads:true});
  await page.goto(url);
  await page.locator("#tab-style").click();
  const button = page.locator("#style-export");
  // Substitute a real origin-private file handle for the interactive OS dialog.
  await page.evaluate(() => {
    window.showSaveFilePicker = async ({suggestedName}) => {
      const root = await navigator.storage.getDirectory();
      window.exported = await root.getFileHandle(suggestedName, {create:true});
      return window.exported;
    };
  });
  await button.click();
  await page.getByText("Saved footage-styles.zip.", {exact:true}).waitFor();
  const bytes = await page.evaluate(async () => Array.from(new Uint8Array(
    await (await window.exported.getFile()).arrayBuffer())));
  assert.ok(bytes.length > 0);
  await writeFile(join(output, "picked.zip"), Buffer.from(bytes));
  await page.evaluate(() => { window.showSaveFilePicker = undefined; });
  const download = page.waitForEvent("download");
  await button.click();
  await (await download).saveAs(join(output, "download.zip"));
  await page.evaluate(() => { window.showSaveFilePicker = async () => {
    throw new DOMException("Cancelled", "AbortError");
  }; });
  await button.click();
  await page.getByText("Export cancelled.").waitFor();
} finally {
  await browser.close();
}
