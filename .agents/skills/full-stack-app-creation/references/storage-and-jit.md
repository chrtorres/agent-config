# Storage telemetry and just-in-time privileged reads

Use this optional worked example when a local app needs Linux storage visibility or a user-authorized privileged read. It complements the monitoring example; it does not prescribe a storage domain or Linux stack for other applications.

Create a fresh task copy:

```sh
python3 -B <skill-directory>/scripts/create_storage_app.py --destination <new-app-directory>
```

Read the copied README for runtime prerequisites and test scopes. The full source and dependency closure are in `assets/storage-app/`: Python collector, API, native authorization worker, frontend, original generic shell input, fixtures, unit/HTTP/browser tests, pinned QA dependencies, and validation runner. The copy helper refuses existing destinations and symlinks entering the skill. External dependencies are acquired separately; privileged device access needs a human and working desktop policy agent.

Read the [portable example instructions](../assets/storage-app/README.md) before running it. The [synthetic example evidence](storage-example-evidence/README.md) includes a safe API snapshot and desktop/mobile images; it carries no original machine's readings.

## User feedback and implementation response

These are curated paraphrases of the completed conversation, not fresh user instructions or approval to repeat privileged actions.

| User feedback | Response and reusable lesson | Evidence scope |
| --- | --- | --- |
| Build visual storage telemetry from a read-only inventory script; proceed without repeated questions. | Created a complete local vertical slice with drive maps, mounted capacity, filters, history, export, responsive states and real data. Resolve routine choices autonomously; local device commands determine the delivery environment. | Original live CLI/HTTP/browser comparisons; portable source retained. |
| Acceptance must be at least 95. | Declared 20 five-point engineering scenarios, mandatory critical gates, and retained source-linked results. Report automated acceptance separately from human SUS or certification. Never adjust the rubric merely to manufacture a pass. | Original automated acceptance reached 100; this is historical scope, not a future guarantee. |
| smartmontools is installed; finish testing. | Rechecked actual access, discovered permission denial remained, exposed real error messages, invalidated missing-tool cache after installation, and compared CLI/API/UI. Installation is not integration success. | Original nonprivileged error reporting was tested; it did not prove hardware health. |
| Get past the blocker securely; provide a button and perhaps a password textarea; launch a local window so I can test. | Added explicit scan action, native desktop authentication, per-process CSRF and exact Origin checks, no password/body API, fixed validated SMART argv and unprivileged web server. Opened the local view for the human. Do not copy the proposed password textarea into the product. | Human completed system prompts; actual device-reported health reached the UI. |
| Password may persist for the session. | Distinguished authority from data. Inspected real policy rather than promising cached credentials. Each privileged query needed fresh authorization on the tested policy; only timestamped results stayed in server memory. Automatic refresh preserves collection age and never opens authentication. | Original human-authorized reads and browser refresh retained results; no passwords stored. |

## Implementation and validation decisions

- Discover root-owned system executable locations at use time. Elevate only a fixed read operation on inventoried devices. Never elevate a user-writable application script, interpreter plus writable script, or the web server. No persistent sudoers/polkit rule is needed for this example. Generic pkexec is still a privileged boundary; examine target policy and exact argv.
- Native authorization is asynchronous. The HTTP action starts one job and returns promptly; the UI polls status. Cancellation/denial/no-agent/timeout stops subsequent prompts. Multiple concurrent scans are rejected. Do not claim global cancellation rolls back already completed reads.
- Cache invalidation must react to tool availability changes. Retained authorized snapshots display their own timestamp and session scope. Reloading the page must not imply a new health measurement.
- Keep missing, denied, unsupported, malformed, failing and healthy states distinct. Capacity is not device health. Unknown unmounted usage is not free capacity. Filesystem reserve and alias deduplication affect totals.
- Test malicious paths, fixed argv, CSRF/Origin/body validation, repeated requests, cancellation and malformed output with mocks. Mocked elevation is not evidence of a real hardware read. The full suite requires explicit read-only live-host scope and never triggers native prompts.
- Inspect settled screenshots. Earlier reviews found contrast failures and cramped mobile tables; labeled volume cards fixed mobile visibility. Modal evidence uses viewport capture, avoiding full-page fixed-position artifacts. An early harness mistakenly awaited a history request after an intentionally aborted snapshot; wait for visible completion on both success and error paths.
- Browser-context construction and QA dependency engine versions matter: use explicit Playwright BrowserContext for axe, lock a compatible adapter, and require an existing discoverable browser.

## Resource selection and provenance

| Material | Disposition |
| --- | --- |
| Complete authored app, shell input, package manifest/lock, tests and validation runner | Bundled under `assets/storage-app`; original task directory is not an import/dependency. |
| Creation helper and refusal/isolated-copy checks | `scripts/create_storage_app.py`, `tests/test_storage_creation.py`. |
| Feedback, interpretation rules, failure corrections and security limits | This reference plus copied PRODUCT/README. |
| Synthetic sample API data and graphical examples | Generated from copied app's demo source; historical examples under `references/storage-example-evidence`. No original host image/data is copied. |
| Original real SMART readings, serial/device identities, hostname, mounts, timestamps, raw HTTP logs and user screenshots | Excluded from shared resources. Remain task-local; preserve the fact and scope of human verification through the feedback table. |
| Runtime database, CSRF tokens, active process/session data, browser profile, authentication state and original delivery archives | Excluded; regenerate in each new task. No password capture. |
| Python, Linux utilities, SMART tools, polkit/desktop agent, Node, browser, QA packages | External prerequisites documented in the copied README; dependencies acquired from the lockfile, not bundled installations. |
| New validation results and screenshots | Store outside the skill, tied to this adapted source; historical passes do not establish current correctness. |

Generalized categories: user/home/workspace paths, host/device/mount identities in evidence, original project and preview identities, local port, process/run identifiers, timestamps, browser installation path, and privileged tool locations. Platform API paths and loopback are platform/protocol constants. Demo/unit device names and labels are explicitly synthetic. No concrete environment-specific value was approved for inclusion, and none is required.
