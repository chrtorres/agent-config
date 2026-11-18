# Dependencies and portable reproduction

## Application and unit checks

The application needs Linux, Python 3.10 or newer, and a modern browser. It has no third-party Python runtime dependency, build step, external service, font download, or credential. Live metrics depend on readable `/proc` and ordinary filesystem metadata. System command availability and privileges vary; missing tools remain gaps rather than being installed automatically.

Node.js 20 or newer is the tested validation baseline. The copied app's `package.json` pins `playwright-core` 1.65.1 as a development dependency; the application does not use Node to run. A compatible existing Chrome/Chromium is required for browser QA. Browser paths are discovered on PATH or supplied with `BROWSER_EXECUTABLE`. Python and Node are invoked from the caller's environment, not from a captured installation path.

## Browser module setup

If `playwright-core` is already available to Node, no install is needed. Otherwise, where isolated developer dependency acquisition is authorized, run from the **copied app**:

```sh
npm ci --ignore-scripts --no-audit --no-fund
```

This installs the declared development dependency locally and does not install a browser or Linux packages. Keep resulting `node_modules` in the task workspace. The bundled lockfile records the public registry resolution and integrity hash for the tested module. A version/lock change needs the affected browser checks rerun.

When using an existing module outside ordinary resolution, set `PLAYWRIGHT_MODULE` to its discovered absolute ES-module entry point or resolvable module specifier. Set `BROWSER_EXECUTABLE` only when PATH discovery is insufficient. `BROWSER_TIMEZONE` optionally selects the user's timezone for screenshots. Do not embed previous task paths in these variables or documentation.

The browser checker uses an existing executable and never downloads a browser. Its launch includes `--no-sandbox`, inherited from the captured controlled local QA setup; use only for these trusted local tests when required by the environment. Use the supported browser infrastructure in environments that prohibit direct automation. If an indispensable browser/module/runtime is unavailable, preserve the non-browser checks and report browser QA blocked rather than inventing a pass.

## Commands

After `scripts/create_app.py` has made a new task-local app, from that directory:

```sh
python3 -B scripts/run_checks.py --output <fresh-evidence-directory> --browser
```

For authorized real-host verification, add `--live-host`. For a dedicated, already running local preview, add `--preview-url <printed-local-url>`. Without `--browser`, only Python/core/syntax checks run and the manifest records that browser QA did not run.

To test the packaging helper itself:

```sh
python3 -B -m unittest discover -s <skill-directory>/tests -v
```

`scripts/capture_examples.mjs` regenerates curated visual references against an isolated **synthetic-only** session. Read its help/usage and the example-evidence provenance before using it. Its timestamp normalization is for reusable illustrative assets, never a substitute for current raw validation evidence.

## Provenance and exclusions

Application, test, and helper code is captured from the completed user workspace and generalized for this bundle. No additional license grant is invented. No third-party dependency source, native executable, font, or binary object is embedded. Playwright and the chosen browser retain the licenses distributed with those products. The synthetic screenshots and JSON examples are generated from the bundled interface and fixture data.

Python, Node, the browser, and the optional npm-resolved development dependency are explicit external prerequisites, not missing authored assets. No account/service dependency, hosting identity, system package installation, or credential is required. Lack of a particular diagnostic command reduces coverage; it does not block launching the dashboard.
