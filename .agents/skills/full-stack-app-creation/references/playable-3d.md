# Playable 3D app regression and delivery

Use this mode for a stateful browser scene with continuous controls, game or simulation rules, and progress that must survive reload. Use the existing app's rendering, input, and storage conventions when expanding a working product.

1. Confirm the Git root and intended remote before the first edit. Similar directory names and shared ancestry do not identify the right checkout. Scope parallel work by file or feature. Ask reviewers to exercise the exact integrated candidate when concurrent changes affect a common input, timing, or save contract.
2. Record hard requirements separately from aesthetic goals. Give each requirement an observable pass condition. Include a representative traversal, visible following camera, meaningful state transition, saved bytes and reload, error recovery, and any device-dependent controls relevant to the app.
3. Separate simulation state from the renderer and browser events. Clamp elapsed time after startup, tab suspension, or an out-of-order animation timestamp. If fixed steps are needed, latch input edges across frames with no step and consume each edge once across frames with several steps. Sample held controls as levels. Keep hit timing and visible animation aligned by reading the same action state.
4. Keep saves on the intended origin and validate their schema before use. Preserve earlier valid progress during a format migration. Report storage denial and recovery. A change to scheme, host, or port selects a different browser storage namespace.
5. Build the production candidate and serve it in an isolated test instance. Drive input through the real page. Wait for rendered observations during motion and for the actual state transition at the end of a journey. Capture runtime and console errors, tested backend and browser versions, screenshots, and the source revision or hashes. Avoid hot reload during acceptance. For slow software rendering, reduce viewport cost or use a verified hardware backend. When splitting suites, record which cases ran and verify that the app source remained identical.
6. Test the physical controller separately if it is a requirement. Record operating-system visibility, browser enumeration and mapping, activation, motion, actions, and reconnect. A synthetic pad establishes the application input path only. Make test input streams explicit so an attached physical pad cannot interfere with a keyboard-only script.

## Reproduce the synthetic checkpoint fixture

```sh
python3 -B <skill-directory>/scripts/create_app.py --example playable-3d --destination <new-app-directory>
cd <new-app-directory>
npm ci
npx playwright install chromium
npm test
npm run build
npm run smoke -- <fresh-evidence-directory-outside-app>
```

The fixture uses Node.js 20.19 or later, npm, locked Vite, Three.js and Playwright, and Chromium with WebGL 2. Playwright may need browser system libraries. The smoke runner allocates and closes its own loopback preview. The default uses SwiftShader. `BROWSER_GPU=1` requests ANGLE OpenGL on a compatible host. Check the browser's renderer before claiming hardware acceleration.

The fixture uses generated primitives. A visible player moves toward a beacon, can activate it in range, changes the rendered beacon state, and persists a versioned save. The unit checks exercise time boundaries, substep input, malformed data and denied storage. The browser fixture drives keyboard and injected controller input, inspects a rendered observation, tests reload, checks console errors, and writes screenshots and outcomes. For authoring a versioned Blender asset, use [runtime GLB](../../3d-modeling/references/runtime-glb.md).

## Capture decision and provenance

The incoming method is adding and validating a persistent real-time 3D application journey. Factors below use the skill capture rubric in order: outcome, inputs, procedure, resources, validation.

| Candidate | Factors | Score | Evidence and routing |
| --- | --- | ---: | --- |
| Full-stack app creation | 1, 1, .75, .5, .75 | 81.25% | Covers the vertical slice, storage and rendered browser verification. The live-state example supplies a 3D rendering and browser-test precedent. Continuous input and simulation timing add new decisions. Extend. |
| 3D modeling | .25, .5, .25, .5, .5 | 35% | Covers model export and browser presentation, with a different result and no gameplay persistence. Route asset authoring there. |
| Smoke test | .25, .25, .5, .25, .75 | 38.75% | Covers isolated rendering evidence and fixture tests. Its viewer matrix lacks rules, input mapping, and progression. Use its visual checks when relevant. |

| Resource | Disposition |
| --- | --- |
| Fixed-step rules, input adapter, renderer, save schema, tests, launch and dependency lock | Bundled as the complete [synthetic fixture](../assets/playable-3d). The same delivery pattern needs no separate backend for this local save contract. |
| Full originating game, campaign content, source and build history | Retained in its task repository. The smaller fixture demonstrates the reusable method independently. The original game is optional reference material. |
| Blender geometry, visual reference, shaders, media and generated artifacts | Runtime-model method and source are captured in the linked modeling extension. The playable fixture generates its geometry. The supplied image and original game visuals remain task-local. |
| Historical test results, failed hot-reload and slow-render attempts, screenshots, device information | Retained outside the skill. Fresh evidence is produced by the fixture. |
| Dependencies, browser, engine and device | Acquired from the lockfile and browser installer. A physical device and supported browser mapping are required for hardware acceptance. |

Historical feedback, paraphrased. The user required regression checks before feature delivery and physical controller support. An apparent controller failure exposed the gap between synthetic tests and native discovery. The user confirmed the connection returned. The physical behavior of new bindings still required hands-on checks. The user also clarified that a similarly named checkout belonged to a separate product. Later delivery used the designated repository; this mode makes repository identity a first-edit check.

In the originating run, the production build passed 150 unit and 59 browser checks. All three checkpoints were traversed with real page inputs. The campaign check exercised victory, defeat, and reload. Extensive hardware input feel and visual equivalence to a reference were outside those automated results.

Generalized values include project and repository identities, branch names, local paths, origin and ports, device identity, evidence locations and run identifiers.
