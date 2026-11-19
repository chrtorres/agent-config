import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join } from "node:path";

const [url, output, packagePath = "playwright"] = process.argv.slice(2);
if (!url || !output) throw new Error("Usage: node check_material_variants.mjs <review-url> <evidence-dir> [playwright-module]");
const base = new URL(url);
const { chromium } = createRequire(import.meta.url)(packagePath);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1040, height: 700 } });
page.setDefaultTimeout(50000);
const passed = [];
const errors = [];
const external = [];
const expect = (condition, label) => {
  assert.ok(condition, label);
  passed.push(label);
};

function resource(slug, file) {
  return new URL(`../variants/${slug}/review/${file}`, base).href;
}

async function ready(slug) {
  await page.locator(`#viewer[data-variety="${slug}"]`).waitFor();
  await page.locator("#loading").waitFor({ state: "hidden" });
}

async function capture(name) {
  // The camera change must reach the rendered frame before comparing screenshots.
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const bytes = await page.locator("canvas").screenshot({ path: join(output, name + ".png") });
  return createHash("sha256").update(bytes).digest("hex");
}

async function select(slug) {
  await page.locator("#variety").selectOption(slug);
  await ready(slug);
}

try {
  for (const file of ["", "styles.css", "viewer.js", "catalog.json", "vendor/build/three.core.js"]) {
    expect((await page.request.head(new URL(file, base).href)).ok(), `HTTP delivery ${file || "index.html"}`);
  }
  const manifest = await (await page.request.get(new URL("catalog.json", base).href)).json();
  const [first, second] = manifest.variants;
  for (const { slug } of manifest.variants) {
    for (const file of ["model.glb", "metadata.json"]) {
      expect((await page.request.head(resource(slug, file))).ok(), `HTTP delivery ${slug} ${file}`);
    }
  }
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== base.origin) external.push(request.url());
  });
  const model = page.waitForResponse(response => response.url() === resource(first.slug, "model.glb"));
  await page.goto(base.href);
  expect((await model).ok(), "browser fetched initial GLB");
  await ready(first.slug);
  expect(await page.locator("canvas").isVisible(), "rendered canvas visible");
  const overview = await capture("overview");
  await page.getByRole("button", { name: "Overhead" }).click();
  const overhead = await capture("overhead-first");
  expect(overview !== overhead, "overhead changes rendered pixels");
  for (const entry of manifest.variants.slice(1)) {
    await select(entry.slug);
    expect(await capture("overhead-" + entry.slug) !== overhead, `distinct appearance for ${entry.slug}`);
    expect(await page.locator("#title").innerText() === entry.label, `metadata for ${entry.slug}`);
    expect(await page.locator("#glb").getAttribute("href") === resource(entry.slug, "model.glb"), `download for ${entry.slug}`);
    expect(new URL(page.url()).searchParams.get("variety") === entry.slug, `shareable variant URL for ${entry.slug}`);
  }
  await select(first.slug);
  expect(await capture("overhead-restored") === overhead, "variant switching preserves camera composition");

  if (manifest.detail) {
    await page.getByRole("button", { name: manifest.detail.label }).click();
    expect(await capture("detail") !== overhead, "configured detail preset changes framing");
  }
  await page.getByRole("button", { name: "Reset view" }).click();
  expect(await capture("reset") === overview, "reset returns to overview");
  const wire = page.getByRole("button", { name: "Wireframe" });
  await wire.click();
  expect(await wire.getAttribute("aria-pressed") === "true", "wireframe selected");
  expect(await capture("wireframe") !== overview, "wireframe visibly renders");
  await wire.click();

  const secondURL = resource(second.slug, "model.glb");
  const reject = route => route.fulfill({ status: 404 });
  await page.route(secondURL, reject);
  await page.locator("#variety").selectOption(second.slug);
  await page.getByText("Could not load", { exact: false }).waitFor();
  expect(await page.locator("#viewer").getAttribute("data-variety") === first.slug, "failure preserves the previously loaded model");
  expect(await page.locator("#variety").inputValue() === first.slug, "failure restores the previous selection");
  await page.unroute(secondURL, reject);
  await select(second.slug);
  expect(await page.locator("#title").innerText() === second.label, "selection succeeds after asset recovery");

  let intercepted;
  const started = new Promise(resolve => { intercepted = resolve; });
  let resume;
  const released = new Promise(resolve => { resume = resolve; });
  await page.route(resource(first.slug, "model.glb"), async route => {
    intercepted();
    await released;
    await route.continue().catch(() => {});
  });
  await page.locator("#variety").selectOption(first.slug);
  await started;
  await page.locator("#variety").selectOption(second.slug);
  resume();
  await ready(second.slug);
  expect(await capture("rapid-switch") !== overview, "canceled selection leaves the latest rendered variant");
  expect(await page.locator("#title").innerText() === second.label, "only latest selection owns metadata");

  await page.setViewportSize({width:390,height:760});
  await page.screenshot({path:join(output,"mobile.png"),fullPage:true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth), "mobile layout fits viewport");
  expect(external.length === 0, "viewer makes no third-party requests");
  expect(errors.length === 0, "viewer has no unhandled page errors");
  assert.ok(passed.length >= 20);
} finally {
  await writeFile(join(output,"results.json"), JSON.stringify({browser:browser.version(), node:process.version, passed}, null, 2)+"\n");
  await browser.close();
}
console.log(`${passed.length} browser checks passed`);
