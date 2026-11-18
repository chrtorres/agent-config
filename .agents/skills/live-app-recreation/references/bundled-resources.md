# Captured implementation kit

Use this kit as a working starting point for a live behavioral recreation. Select the pieces that fit the requested app. All bundled code uses synthetic workspace content; no deployment identity or external service credential is included. The generalized UI uses system-font fallbacks and has no remote font or image dependency.

## Inventory

| Location | Contents |
|---|---|
| `assets/python-agent/agent.py` | Portable workspace tools, streamed HTTP client, approvals, agent loop, conversation save/load |
| `assets/python-agent/mock_server.py` | Deterministic HTTP/SSE model fixture with fragmented tool-call arguments and error cases |
| `assets/python-agent/demo.py` | End-to-end demonstration with retained requests, transcript and files; optional separately configured real-model CLI |
| `assets/web-app/` | Complete static HTML/CSS/JavaScript phone interface, behavioral core, file browser, conversations, approvals, settings and animations |
| `tests/test_agent.py` | Python integration tests: wire format, streaming, tools, file outcomes, approvals, containment, errors, bounded execution and persistence |
| `tests/test-engine.mjs` | Direct browser-core assertions for file tools, edits, containment and deterministic plans |
| `tests/browser-check.mjs` | Chrome/Chromium-driven UI checks, complete walkthrough, persistence, mobile layout and screenshots |
| `scripts/serve.py` | Static preview launcher with a configurable host and OS-selected port |
| `scripts/run_checks.py` | Isolated validation runner with command logs, generated demo evidence and source hashes |
| `references/sample-evidence/` | Sanitized synthetic transcript, observed requests, demonstration assertions and resulting workspace files |
| `assets/reference-images/` | Screenshots of the generalized starter, generated through the browser test |
| `references/bundle-index.json` | Skill-relative inventory, file sizes and SHA-256 hashes for the captured resources |

Paths above are relative to the skill directory. Resolve that directory from the loaded skill rather than assuming a model-specific installation path.

## Fidelity and architecture

The Python example exercises actual HTTP exchanges against a loopback fixture. Its tool loop consumes streamed responses, executes local filesystem operations in an isolated Documents directory, and returns tool results to the fixture. The fixture scripts calls; it is not a neural model.

The browser example implements its own JavaScript workspace and action planner. Files live in browser storage. It does not call the Python backend. Its animated text is a UI effect, not network streaming. This separation makes a static live presentation portable, but both implementations need their own tests.

The bundled interface supports chat, read/create/edit/search, expandable tool cards, mutation approvals, file viewing/downloading, conversation history, stop, persistent settings, reset, export and a guided walkthrough. It omits native APIs, real model inference, private platform access and platform-specific services. Provider options are explicitly display previews.

Before adopting this template for a different app, replace the planner and fixture scenarios with the intended behavior. Compare observed outputs to a specification or available original implementation; passing these synthetic tests establishes the starter's behavior, not a new application's equivalence.

## Run the kit

Replace the following path placeholders with locations discovered in the current environment. Evidence must be written outside the skill. The runner refuses an existing demonstration output directory to avoid silently reusing artifacts.

```sh
python3 <skill-directory>/scripts/run_checks.py --output <fresh-evidence-directory>
```

This runs Python tests and the recorded HTTP demonstration, then the JavaScript engine checks and application syntax check. Python and Node must already be available; missing prerequisites are recorded as blocked or failed commands, not passing checks.

For a live static preview:

```sh
python3 <skill-directory>/scripts/serve.py
```

The script prints the selected local URL. Use that URL rather than a remembered port. It can also serve a copied project with `--directory <static-directory>`. Browser state and demonstration changes are not written into shared source.

## Browser validation

First follow the environment's permitted browser and preview mechanisms. This kit does not authorize installing a browser, bypassing managed preview restrictions, or publishing a site. On an environment that permits direct Chrome/Chromium automation, use an available Playwright Core module and compatible browser.

The browser checker imports `playwright-core` through normal module resolution unless `PLAYWRIGHT_MODULE` supplies a resolvable module specifier or absolute module path. It discovers common browser commands on `PATH`; `BROWSER_EXECUTABLE` can select an existing browser. Dependencies belong in a task-local or scratch installation, outside the shared skill.

```sh
PLAYWRIGHT_MODULE=<module-path-or-specifier> BROWSER_EXECUTABLE=<browser-executable> python3 <skill-directory>/scripts/run_checks.py --output <fresh-evidence-directory> --browser
```

The runner starts and tears down a local preview for this optional test. Pass `--preview-url <running-preview-url>` to use an existing preview instead. Tests assume the bundled interface and storage schema. Adapt selectors and expectations after modifying the app.

The UI test drives denial and approval, edits and file inspection, traversal blocking, reload persistence, stop, conversation history, reset, and the entire walkthrough through real controls. It also checks a synthetic narrow viewport and captures screenshots. A narrow viewport is not a device execution test.

## Evidence, data and portability

Sample JSON under `sample-evidence/` is illustrative historical fixture data. A placeholder server origin replaces run-specific network addresses. The screenshots depict the generalized template rather than a native application. Neither substitutes for running the current source.

The sample folder also retains the Python and JavaScript test logs, browser assertion results, and a portable validation summary. Machine-specific commands, host details and absolute paths remain in the external validation evidence rather than these shared examples.

The validation runner records actual command arguments, working directories, runtime/host details, exit codes, logs, source SHA-256 values, generated requests and files. Those fresh environment values stay in its external evidence directory. Browser screenshots and a check summary are produced when browser validation runs. Visual review is still required; assertions can pass while presentation is poor.

Excluded from the reusable kit: original Git metadata, dependency installations, provider credentials, hosting manifests with project IDs, private deployment URLs, machine-specific manifests, and unsanitized task artifacts. Keep those in the original task evidence when needed; do not infer permission to put concrete environment values into a reusable skill.

## Operational lessons preserved

- Use explicit context-manager cleanup for the Python tests so they work on runtimes without newer unittest convenience APIs.
- Open the settings screen before clicking a settings control; a hidden element found by a selector is not interactable.
- Judge mutations by stored bytes and rendered file content, not assistant claims.
- Wait for completed UI state and settled paint before capturing screenshots.
- Keep approval choices real. A walkthrough pauses for the user, while automation supplies deliberate test decisions.
- Bind preview servers to a local interface by default and choose free ports dynamically.
- Stop stale runs from completing after cancellation; inspect pending approvals as well as the composer.
- Reuse persisted hosting identity and exact tested source/build through the active hosting workflow; this kit intentionally contains no copied site identity.
