import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { appendFile, cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { delimiter, dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const repository = fileURLToPath(new URL('../', import.meta.url));
const option = process.argv.indexOf('--evidence');
const evidenceArgument = option === -1 ? process.env.ACTIVITY_TOWN_SMOKE_EVIDENCE : process.argv[option + 1];
if (!evidenceArgument) {
  throw new Error('Use npm run smoke -- --evidence <new directory outside the repository>.');
}

const evidence = resolve(evidenceArgument);
const relativeEvidence = relative(repository, evidence);
if (relativeEvidence.split(/[\\/]/)[0] !== '..' && !isAbsolute(relativeEvidence)) {
  throw new Error('Keep smoke evidence outside the application repository.');
}
await mkdir(dirname(evidence), { recursive: true });
await mkdir(evidence);

const copy = join(evidence, 'checkout');
const workspace = join(evidence, 'fixture-workspace');
const demoHome = join(evidence, 'demo-codex');
const liveHome = join(evidence, 'live-codex');
const results = [];
const desktopInteractionViewport = { width: 1000, height: 790 };
const desktopDeviceScale = .75;
const travelTimeout = 60_000;
const sourceFiles = [
  '.gitignore', 'README.md', 'index.html', 'package.json', 'package-lock.json',
  'scripts', 'src', 'vite.config.js'
];
const runtime = { node: process.version };
const consoleErrors = [];
const failedRequests = [];

async function check(name, action, required = false) {
  const started = Date.now();
  try {
    const detail = await action();
    results.push({ name, status: 'pass', durationMs: Date.now() - started, detail });
    console.log(`PASS ${name}`);
  } catch (error) {
    results.push({ name, status: 'fail', durationMs: Date.now() - started, detail: error.message });
    console.error(`FAIL ${name}\n${error.message}`);
    if (required) throw error;
  }
}

function command(program, args, cwd = repository) {
  return spawnSync(program, args, { cwd, encoding: 'utf8', timeout: 120_000 });
}

async function runCommand(name, program, args) {
  const result = command(program, args, copy);
  await writeFile(join(evidence, name), (result.stdout || '') + (result.stderr || ''));
  assert.equal(result.status, 0, result.error?.message || `See ${name}`);
}

async function waitFor(read, accept, description, timeout = 12_000) {
  const deadline = Date.now() + timeout;
  let value;
  do {
    value = await read();
    if (accept(value)) return value;
    await delay(100);
  } while (Date.now() < deadline);
  throw new Error(`Timed out waiting for ${description}. Last value was ${JSON.stringify(value)}.`);
}

async function startServer(home, name) {
  let output = '';
  const child = spawn(process.execPath, ['scripts/serve.mjs'], {
    cwd: copy,
    env: { ...process.env, PORT: '0', ACTIVITY_TOWN_CODEX_HOME: home, ACTIVITY_TOWN_WORKSPACE: workspace, ACTIVITY_TOWN_SESSION_ID: '' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', (chunk) => { output += chunk; });
  child.stderr.on('data', (chunk) => { output += chunk; });
  const finished = new Promise((done) => child.once('close', done));
  const stop = async () => {
    child.kill();
    await finished;
    await writeFile(join(evidence, name + '-server.log'), output);
  };
  try {
    const url = await waitFor(
      () => output.match(/http:\/\/127\.0\.0\.1:\d+/)?.[0],
      Boolean,
      'a loopback server port',
      8_000,
    );
    return { url, stop };
  } catch (error) {
    await stop();
    throw error;
  }
}

function observe(page, scope) {
  page.setDefaultTimeout(30_000);
  page.on('pageerror', (error) => consoleErrors.push(`${scope}: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(`${scope}: ${message.text()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400) failedRequests.push(`${scope}: ${response.status()} ${new URL(response.url()).pathname}`);
  });
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
      failedRequests.push(`${scope}: ${request.failure()?.errorText} ${new URL(request.url()).pathname}`);
    }
  });
}

const coordinates = {
  office: [0, 4.95],
  documents: [-17, 4.25],
  pictures: [13.62, -0.38],
  workshop: [12, 14.2],
};

function position(canvas, object) {
  return canvas.evaluate((element, name) => ['X', 'Y', 'Z'].map((axis) => Number(element.dataset[name + axis])), object);
}

async function nearBuilding(canvas, building) {
  const [x, z] = coordinates[building];
  return waitFor(
    () => position(canvas, 'agent'),
    ([actualX, , actualZ]) => Math.hypot(actualX - x, actualZ - z) < 1.5,
    `the agent to arrive at ${building}`,
    travelTimeout,
  );
}

async function shows(locator, pattern) {
  return waitFor(() => locator.textContent(), (text) => pattern.test(text), String(pattern));
}

async function screenshotPixels(page, canvas, filename) {
  const png = await canvas.screenshot();
  await writeFile(join(evidence, filename), png);
  return page.evaluate(async (base64) => {
    const image = new Image();
    image.src = 'data:image/png;base64,' + base64;
    await image.decode();
    const buffer = document.createElement('canvas');
    buffer.width = 96;
    buffer.height = 72;
    const context = buffer.getContext('2d');
    context.drawImage(image, 0, 0, buffer.width, buffer.height);
    const pixels = context.getImageData(0, 0, buffer.width, buffer.height).data;
    const colorBuckets = new Set();
    let saturatedPixels = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      const red = pixels[index];
      const green = pixels[index + 1];
      const blue = pixels[index + 2];
      colorBuckets.add([red >> 4, green >> 4, blue >> 4].join(','));
      if (Math.max(red, green, blue) - Math.min(red, green, blue) >= 30) saturatedPixels += 1;
    }
    return { width: image.width, height: image.height, uniqueColorBuckets: colorBuckets.size, saturatedPixels };
  }, png.toString('base64'));
}

async function floorDifference(page, before, after) {
  return page.evaluate(async (captures) => {
    const sample = document.createElement('canvas');
    sample.width = 180;
    sample.height = 112;
    const context = sample.getContext('2d', { willReadFrequently: true });
    // Fractional device scaling can antialias the same geometry differently between captures.
    context.filter = 'blur(1px)';
    const pixels = [];
    for (const capture of captures) {
      const image = new Image();
      image.src = 'data:image/png;base64,' + capture;
      await image.decode();
      context.drawImage(image, image.width * .32, image.height * .16, image.width * .38, image.height * .48,
        0, 0, sample.width, sample.height);
      pixels.push(context.getImageData(0, 0, sample.width, sample.height).data);
    }
    let changed = 0;
    for (let index = 0; index < pixels[0].length; index += 4) {
      const difference = [0, 1, 2].reduce((sum, channel) =>
        sum + Math.abs(pixels[0][index + channel] - pixels[1][index + channel]), 0);
      if (difference > 45) changed += 1;
    }
    return changed / (sample.width * sample.height);
  }, [before, after].map((bytes) => bytes.toString('base64')));
}

function sessionLine(type, payload) {
  return JSON.stringify({ timestamp: new Date().toISOString(), type, payload }) + '\n';
}

async function makeFixture(home, cwd, id, name, tool = 'image_gen') {
  const now = new Date();
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const dir = join(home, 'sessions', year, month, day);
  await mkdir(dir, { recursive: true });
  const file = join(dir, `rollout-${year}-${month}-${day}T00-00-00-${id}.jsonl`);
  await writeFile(file, [
    sessionLine('session_meta', { id, cwd }),
    sessionLine('event_msg', { type: 'task_started' }),
    sessionLine('response_item', {
      type: 'function_call',
      name: tool,
      arguments: JSON.stringify({ path: name, prompt: 'private fixture prompt' }),
    }),
  ].join(''));
  return file;
}

async function verifyDemo(browser, server) {
  let page;
  let canvas;
  await check('Production entry point returns HTTP 200 and HTML', async () => {
    const response = await fetch(server.url);
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /text\/html/);
  }, true);
  await check('Activity endpoint serves scoped demo JSON for unrelated sessions', async () => {
    const response = await fetch(server.url + '/api/activity');
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /application\/json/);
    assert.equal((await response.json()).source, 'demo');
  }, true);
  await check('The loopback relay rejects other origins and keeps review files private', async () => {
    const response = await fetch(server.url + '/api/activity', { headers: { Origin: 'https://example.test' } });
    assert.equal(response.status, 403);
    assert.equal(response.headers.get('access-control-allow-origin'), null);
    assert.equal(response.headers.get('cross-origin-resource-policy'), 'same-origin');
    for (const path of ['/.env', '/review/activity-town.png', '/scripts/activity.mjs']) {
      assert.equal((await fetch(server.url + path)).status, 404);
    }
  });
  await check('Desktop browser opens the production town', async () => {
    page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
      deviceScaleFactor: desktopDeviceScale
    });
    observe(page, 'desktop');
    const response = await page.goto(server.url);
    assert.equal(response.status(), 200);
    canvas = page.getByTestId('town-canvas');
    await canvas.waitFor({ state: 'visible' });
  }, true);
  await check('Bundled JavaScript and stylesheet are delivered', async () => {
    const urls = await page.evaluate(() => [
      document.querySelector('script[type=module][src]')?.src,
      document.querySelector('link[rel=stylesheet]')?.href,
    ]);
    assert.ok(urls.every(Boolean));
    const responses = await Promise.all(urls.map((url) => fetch(url)));
    assert.ok(responses.every((response) => response.status === 200));
    assert.match(responses[0].headers.get('content-type'), /javascript/);
    assert.match(responses[1].headers.get('content-type'), /text\/css/);
  });
  await check('Browser has a working WebGL renderer', async () => {
    const version = await page.evaluate(() => {
      const scratch = document.createElement('canvas');
      const gl = scratch.getContext('webgl2');
      return gl?.getParameter(gl.VERSION);
    });
    assert.match(version, /WebGL 2/);
    runtime.webgl = version;
    await waitFor(() => canvas.getAttribute('data-rendered'), (value) => value === 'true', 'the first Three.js render');
  }, true);
  await check('Canvas contains visible multicolored 3D geometry', async () => {
    const pixels = await screenshotPixels(page, canvas, 'desktop-canvas.png');
    assert.ok(pixels.width >= 600 && pixels.height >= 450, JSON.stringify(pixels));
    assert.ok(pixels.uniqueColorBuckets >= 40 && pixels.saturatedPixels >= 150, JSON.stringify(pixels));
    await page.screenshot({ path: join(evidence, 'desktop.png') });
    return pixels;
  });
  await page.setViewportSize(desktopInteractionViewport);
  await check('Demo mode is clearly labeled', () => shows(page.getByTestId('status-source'), /demo|sample/i));
  await check('The agent has a visible marker', () => page.getByTestId('agent-marker').waitFor({ state: 'visible' }));
  await check('Paused sample begins at the office', async () => {
    const control = page.getByTestId('demo-play');
    const label = (await control.getAttribute('aria-label')) || (await control.textContent());
    if (/pause/i.test(label)) await control.click();
    await page.getByTestId('building-office').click();
    await nearBuilding(canvas, 'office');
  });
  await check('Follow camera is selectable', async () => {
    const control = page.getByTestId('follow-camera');
    await control.click();
    assert.equal(await control.getAttribute('aria-pressed'), 'true');
  });
  await check('Overview camera is selectable', async () => {
    const control = page.getByTestId('overview-camera');
    await control.click();
    assert.equal(await control.getAttribute('aria-pressed'), 'true');
  });
  await check('The height slider changes the real camera elevation', async () => {
    const slider = page.getByTestId('camera-height');
    const original = await position(canvas, 'camera');
    await slider.focus();
    await slider.press('End');
    await waitFor(() => position(canvas, 'camera'), (next) => Math.abs(original[1] - next[1]) > 3, 'height slider to change camera elevation');
  });
  let resetOverviewPosition;
  const waitForOverviewReset = () => {
    assert.ok(resetOverviewPosition, 'The Overview reset must be verified first');
    return waitFor(
      () => position(canvas, 'camera'),
      (next) => next.every((value, index) => Math.abs(value - resetOverviewPosition[index]) < .1),
      'a rendered frame at the reset Overview position',
    );
  };
  await check('Reset restores the town camera', async () => {
    const before = await position(canvas, 'camera');
    await page.getByTestId('camera-reset').click();
    resetOverviewPosition = await waitFor(
      () => position(canvas, 'camera'),
      (next) => Math.hypot(...next.map((value, index) => value - before[index])) > 3,
      'camera reset',
    );
  });
  await check('Zoom in moves the camera closer', async () => {
    const before = await position(canvas, 'camera');
    await page.getByTestId('camera-zoom-in').click();
    await waitFor(() => position(canvas, 'camera'), (next) => Math.hypot(...next) < Math.hypot(...before) - 1, 'zoom in');
  });
  await check('Zoom out moves the camera farther away', async () => {
    const before = await position(canvas, 'camera');
    await page.getByTestId('camera-zoom-out').click();
    await waitFor(() => position(canvas, 'camera'), (next) => Math.hypot(...next) > Math.hypot(...before) + 1, 'zoom out');
  });
  await check('Right-button drag pans the aerial view', async () => {
    const bounds = await canvas.boundingBox();
    const slider = page.getByTestId('camera-height');
    const elevation = await slider.inputValue();
    const before = await position(canvas, 'camera');
    const x = bounds.x + bounds.width * 0.60;
    const y = bounds.y + bounds.height * 0.35;
    await page.mouse.move(x, y);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(x + 180, y, { steps: 10 });
    await page.mouse.up({ button: 'right' });
    await waitFor(() => position(canvas, 'camera'), (next) => Math.hypot(next[0] - before[0], next[2] - before[2]) > 3, 'the camera to pan');
    assert.equal(await slider.inputValue(), elevation);
    await page.getByTestId('camera-reset').click();
  });
  await check('Pointer drag changes the aerial viewing angle', async () => {
    const bounds = await canvas.boundingBox();
    const originalElevation = Number(await page.getByTestId('camera-height').inputValue());
    const x = bounds.x + bounds.width * 0.60;
    const y = bounds.y + bounds.height * 0.35;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 145, y + 35, { steps: 10 });
    await page.mouse.up();
    await waitFor(
      () => page.getByTestId('camera-height').inputValue(),
      (next) => Math.abs(Number(next) - originalElevation) > 3,
      'camera angle to change',
    );
  });
  const floor = page.getByTestId('floor-view');
  let bothFloors;
  let bothImage;
  let groundImage;
  let upperImage;
  await check('The office starts with both floors shown', async () => {
    await page.getByTestId('camera-reset').click();
    await waitForOverviewReset();
    await shows(floor, /both floors/i);
    bothFloors = await canvas.getAttribute('data-floors');
    assert.ok(bothFloors);
    bothImage = await canvas.screenshot();
    await writeFile(join(evidence, 'office-both-floors.png'), bothImage);
  });
  await check('The ground-floor control changes the office cutaway', async () => {
    await floor.click();
    await shows(floor, /ground floor/i);
    await waitFor(() => canvas.getAttribute('data-floors'), (value) => Boolean(value) && value !== bothFloors, 'ground-floor geometry state');
    groundImage = await canvas.screenshot();
    const changed = await floorDifference(page, bothImage, groundImage);
    assert.ok(changed > .05, `Ground floor changed only ${(100 * changed).toFixed(1)}% of the Town Hall pixels`);
    return { changed };
  });
  await check('The upper-floor control changes the office cutaway', async () => {
    const ground = await canvas.getAttribute('data-floors');
    await floor.click();
    await shows(floor, /upper floor/i);
    await waitFor(() => canvas.getAttribute('data-floors'), (value) => Boolean(value) && value !== ground && value !== bothFloors, 'upper-floor geometry state');
    upperImage = await canvas.screenshot();
    const changed = await floorDifference(page, groundImage, upperImage);
    assert.ok(changed > .05, `Upper floor changed only ${(100 * changed).toFixed(1)}% of the Town Hall pixels`);
    await page.screenshot({ path: join(evidence, 'office-upper-floor.png') });
    return { changed };
  });
  await check('The office cutaway can return to both floors', async () => {
    await floor.click();
    await shows(floor, /both floors/i);
    await waitFor(() => canvas.getAttribute('data-floors'), (value) => value === bothFloors, 'both-floor geometry state');
    const restored = await canvas.screenshot();
    await writeFile(join(evidence, 'office-restored.png'), restored);
    const baselineDifference = await floorDifference(page, bothImage, restored);
    const cutawayDifference = await floorDifference(page, upperImage, restored);
    assert.ok(baselineDifference < .025, `Restored view differs from the original by ${(100 * baselineDifference).toFixed(1)}%`);
    assert.ok(cutawayDifference > .05);
    return { baselineDifference, cutawayDifference };
  });
  await check('Following the agent moves the camera with its first trip', async () => {
    await page.getByTestId('follow-camera').click();
    await nearBuilding(canvas, 'office');
    const before = await position(canvas, 'camera');
    await page.getByTestId('building-documents').click();
    await waitFor(() => position(canvas, 'camera'), (next) => Math.abs(next[0] - before[0]) > 3, 'camera to follow the agent');
  });
  await check('The agent walks to Documents', async () => {
    const arrival = await nearBuilding(canvas, 'documents');
    await shows(page.getByTestId('agent-location'), /documents/i);
    return arrival;
  });
  await check('Follow mode keeps Codex in frame at full zoom', async () => {
    const marker = page.getByTestId('agent-marker');
    const button = page.getByTestId('camera-zoom-in');
    for (let index = 0; index < 10; index++) await button.click();
    await waitFor(async () => {
      const agent = await marker.boundingBox();
      const view = await canvas.boundingBox();
      return Boolean(agent && agent.x > view.x + view.width * .2 && agent.x < view.x + view.width * .8);
    }, Boolean, 'Codex to remain centered at full zoom');
    await page.getByTestId('camera-reset').click();
  });
  await check('Choosing Follow reacquires Codex after panning the Overview', async () => {
    await page.getByTestId('overview-camera').click();
    await page.getByTestId('camera-reset').click();
    const beforePan = await waitForOverviewReset();
    const marker = page.getByTestId('agent-marker');
    const view = await canvas.boundingBox();
    for (let pan = 0; pan < 12 && await marker.isVisible(); pan++) {
      const x = view.x + view.width * .1;
      const y = view.y + view.height * .23;
      await page.mouse.move(x, y);
      await page.mouse.down({ button: 'right' });
      await page.mouse.move(x + view.width * .8, y, { steps: 10 });
      await page.mouse.up({ button: 'right' });
      await delay(250);
    }
    const afterPan = await position(canvas, 'camera');
    assert.ok(Math.hypot(...afterPan.map((value, index) => value - beforePan[index])) > 8);
    await waitFor(() => marker.isVisible(), (visible) => !visible, 'Codex to be out of frame after manual pan');
    await page.getByTestId('follow-camera').click();
    await waitFor(() => marker.isVisible(), Boolean, 'Follow to frame Codex again');
  });
  await check('Overview holds its camera position while Codex travels', async () => {
    await page.getByTestId('overview-camera').click();
    await page.getByTestId('camera-reset').click();
    const initialCamera = await waitForOverviewReset();
    const before = await position(canvas, 'agent');
    await page.getByTestId('building-pictures').click();
    await waitFor(
      () => position(canvas, 'agent'),
      (next) => Math.abs(next[0] - before[0]) > 8,
      'Codex to move across town',
      travelTimeout,
    );
    const currentCamera = await position(canvas, 'camera');
    const delta = Math.hypot(...currentCamera.map((value, index) => value - initialCamera[index]));
    assert.ok(delta < .5, `Overview moved ${delta.toFixed(2)} units during a trip`);
    await page.getByTestId('follow-camera').click();
  });
  for (const [building, name] of [['pictures', 'My Pictures'], ['workshop', 'Workshop'], ['office', 'Town Hall']]) {
    await check(`The agent walks to ${name}`, async () => {
      await page.getByTestId('building-' + building).click();
      const arrival = await nearBuilding(canvas, building);
      await shows(page.getByTestId('agent-location'), new RegExp(building === 'office' ? 'office|town hall|headquarters|hq' : name, 'i'));
      return arrival;
    });
  }
  await check('The desktop emits no browser errors or failed requests', () => {
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failedRequests, []);
  });
  await page.close();

  let mobile;
  await check('Mobile layout stays inside a 390-pixel viewport', async () => {
    mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    observe(mobile, 'mobile');
    await mobile.goto(server.url);
    await mobile.getByTestId('town-canvas').waitFor({ state: 'visible' });
    const sizes = await mobile.evaluate(() => ({ root: document.documentElement.scrollWidth, window: window.innerWidth }));
    assert.ok(sizes.root <= sizes.window + 1, JSON.stringify(sizes));
  }, true);
  await check('Mobile can open and use the camera menu', async () => {
    const menu = mobile.getByTestId('camera-menu');
    await menu.click();
    await mobile.getByTestId('view-menu').waitFor({ state: 'visible' });
    await mobile.getByTestId('overview-camera').click();
    assert.equal(await mobile.getByTestId('overview-camera').getAttribute('aria-pressed'), 'true');
    await mobile.screenshot({ path: join(evidence, 'mobile.png') });
  });
  await mobile.close();
}

async function verifyLive(browser, server, file, privatePath, sessionId) {
  let page;
  let canvas;
  await check('Structured session data reaches the loopback live API', async () => {
    const response = await fetch(server.url + '/api/activity');
    const body = await response.json();
    assert.equal(body.source, 'live');
    assert.equal(body.session.state, 'working');
    assert.equal(body.session.location, 'pictures');
  }, true);
  await check('Live API omits fixture paths and private prompt text', async () => {
    const text = await (await fetch(server.url + '/api/activity')).text();
    assert.ok(!text.includes(privatePath));
    assert.ok(!text.includes('private fixture prompt'));
    assert.ok(!text.includes(workspace));
    assert.ok(!text.includes(sessionId));
    assert.deepEqual(Object.keys(JSON.parse(text).session).sort(), ['id', 'label', 'location', 'state', 'updatedAt']);
  });
  await check('The browser labels fixture activity as live and heads to My Pictures', async () => {
    page = await browser.newPage({
      viewport: desktopInteractionViewport,
      deviceScaleFactor: desktopDeviceScale
    });
    observe(page, 'live');
    await page.goto(server.url);
    await shows(page.getByTestId('status-source'), /live|connected/i);
    canvas = page.getByTestId('town-canvas');
    await canvas.waitFor({ state: 'visible' });
    await shows(page.getByTestId('agent-location'), /pictures/i);
    return nearBuilding(canvas, 'pictures');
  }, true);
  await check('Live API classifies document and development tools by destination', async () => {
    for (const [name, location] of [
      ['mcp__codex_apps__codex_document_control__list_document_sessions', 'documents'],
      ['exec_command', 'workshop'],
    ]) {
      await appendFile(file, sessionLine('response_item', { type: 'function_call', name }));
      await waitFor(
        async () => (await (await fetch(server.url + '/api/activity')).json()).session,
        (session) => session?.state === 'working' && session.location === location,
        `live ${location} classification`,
      );
    }
  });
  await check('Live session finishes and returns the agent to Town Hall', async () => {
    await appendFile(file, sessionLine('event_msg', { type: 'task_complete' }));
    await waitFor(
      async () => (await (await fetch(server.url + '/api/activity')).json()).session,
      (session) => session?.state === 'idle' && session.location === 'office',
      'completed-session activity',
    );
    await nearBuilding(canvas, 'office');
    await shows(page.getByTestId('agent-location'), /office|town hall|headquarters|hq/i);
    await page.screenshot({ path: join(evidence, 'live-idle.png') });
  });
  await check('Live status stays distinct from demo while activity service recovers', async () => {
    const endpoint = '**/api/activity';
    await page.route(endpoint, (route) => route.fulfill({ json: { source: 'unavailable' } }));
    try {
      await shows(page.getByTestId('status-source'), /offline/i);
      assert.equal(await page.getByTestId('demo-play').isVisible(), false);
      await shows(page.getByTestId('agent-location'), /town hall/i);
    } finally {
      await page.unroute(endpoint);
    }
    await shows(page.getByTestId('status-source'), /live/i);
  });
  await page.close();
  await check('A newer local session takes over automatic tracking', async () => {
    const before = await (await fetch(server.url + '/api/activity')).json();
    await makeFixture(liveHome, workspace, randomUUID(),
      '/fixtures/new-session/reference.md', 'read_document');
    const result = await waitFor(async () => (await (await fetch(server.url + '/api/activity')).json()).session,
      (session) => session?.id !== before.session.id && session?.location === 'documents',
      'the newly active session to be selected',
      8_000);
    assert.equal(result.state, 'working');
  });
}

let browser;
let fatalError;
try {
  const authoringHead = command('git', ['rev-parse', 'HEAD']);
  const authoringBranch = command('git', ['branch', '--show-current']);
  const authoringStatus = command('git', ['status', '--porcelain=v1']);
  runtime.checkout = {
    branch: authoringBranch.stdout?.trim(),
    commit: authoringHead.status === 0 ? authoringHead.stdout.trim() : 'uncommitted',
    changes: authoringStatus.stdout?.trim().split('\n').filter(Boolean).length ?? null,
  };
  await check('Source is copied into a retained isolated checkout', async () => {
    await mkdir(copy);
    for (const path of sourceFiles) {
      await cp(join(repository, path), join(copy, path), {
        recursive: true,
        filter: (file) => !relative(repository, file).split(/[\\/]/).some((part) => (
          part.startsWith('.env') || /\.(jsonl|key|pem|p12|pfx)$/i.test(part)
        ))
      });
    }
    assert.ok(!existsSync(join(copy, '.git')));
    assert.ok(!existsSync(join(copy, 'node_modules')));
  }, true);
  await check('Isolated checkout installs from the dependency lockfile', () => runCommand('npm-ci.log', 'npm', ['ci']), true);
  await check('Relay startup and workspace isolation regression tests pass', () =>
    runCommand('activity-tests.log', process.execPath, ['--test', 'scripts/activity.test.mjs']), true);
  await check('Isolated checkout builds the production application', () => runCommand('npm-build.log', 'npm', ['run', 'build']), true);
  await mkdir(workspace);
  await makeFixture(demoHome, join(evidence, 'other-workspace'), randomUUID(), '/fixtures/unrelated/private.gif');
  await check('Chromium launches for WebGL testing', async () => {
    const browsers = process.platform === 'win32' ? ['chrome.exe', 'msedge.exe'] : ['google-chrome', 'chromium', 'chromium-browser'];
    const defaultBrowser = (process.env.PATH ?? '').split(delimiter)
      .filter(Boolean)
      .flatMap((directory) => browsers.map((name) => join(directory, name)))
      .find(existsSync);
    browser = await chromium.launch({
      executablePath: process.env.BROWSER_PATH || defaultBrowser,
      args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    });
    runtime.browser = browser.version();
  }, true);
  const demoServer = await startServer(demoHome, 'demo');
  try {
    await verifyDemo(browser, demoServer);
  } finally {
    await demoServer.stop();
  }
  const privatePath = '/fixtures/private-pictures/reference.png';
  const sessionId = randomUUID();
  const file = await makeFixture(liveHome, workspace, sessionId, privatePath);
  const liveServer = await startServer(liveHome, 'live');
  try {
    await verifyLive(browser, liveServer, file, privatePath, sessionId);
  } finally {
    await liveServer.stop();
  }
  await check('Mobile and live renderings emit no browser errors or failed requests', () => {
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failedRequests, []);
  });
} catch (error) {
  fatalError = error.message;
  console.error(error);
} finally {
  await browser?.close();
  const passed = results.filter((item) => item.status === 'pass').length;
  const failed = results.length - passed;
  const dependencies = JSON.parse(await readFile(join(repository, 'package.json'), 'utf8'));
  runtime.three = dependencies.dependencies?.three;
  runtime.playwright = dependencies.devDependencies?.playwright;
  await writeFile(join(evidence, 'smoke-results.json'), JSON.stringify({
    runtime,
    passed,
    failed,
    fatalError,
    results,
  }, null, 2) + '\n');
  console.log(`${passed} passed, ${failed} failed. Evidence at ${evidence}`);
  if (passed < 20 || failed || fatalError) process.exitCode = 1;
}
