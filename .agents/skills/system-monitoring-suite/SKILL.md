---
name: system-monitoring-suite
description: Build and browser-test a local Linux system monitoring and troubleshooting dashboard with read-only diagnostics, live resource charts, inspectable command evidence, explicit coverage limits, and portable validation artifacts.
---

# System Monitoring Suite

Build an operable local dashboard joining cautious Linux diagnosis with an inspectable graphical interface. The bundle includes the complete Python/HTTP/browser starter and tests; no earlier task directory or sibling skill is required.

## Establish the target and boundaries

Read workspace instructions and existing source. Identify the target Linux host, symptoms, required views, and whether the user wants an application, extension, or verification of a user-applied repair. Building or packaging an app does not authorize inspecting an unrelated host or applying repairs.

Use existing permissions and local observations. Do not run sudo, package-manager maintenance, service changes, cleanup, mounts, repairs, reboots, SMART self-tests, stress tests, or remote probes as diagnostics. Keep raw evidence local and save it only to an authorized destination. Avoid expensive scans. Missing tools and restricted access are unverified coverage.

Read [diagnostic-contract.md](references/diagnostic-contract.md) before changing collectors or interpretations. Read [architecture-and-qa.md](references/architecture-and-qa.md) for the UI, HTTP boundary, and validation sequence. The source and object inventory is in [resources.md](references/resources.md).

## Create a task-local application

Discover runtime paths, browser tooling, free ports, and artifact destinations. Read [dependencies.md](references/dependencies.md) for prerequisites and isolated dependency setup. Use the active environment's supported preview/browser workflow; when website tooling applies, follow its current local-preview guidance. Keep this host-reading suite local unless a different architecture and data flow are explicitly authorized.

```sh
python3 -B <skill-directory>/scripts/create_app.py --destination <new-app-directory>
```

The helper refuses existing destinations and destinations inside the shared skill. It copies [assets/monitoring-app](assets/monitoring-app), including source, UI assets, documentation, tests, fixtures, format contracts, and validation launcher. Work on the copy; do not store task state in shared resources.

Start the copied app using `python3 -B server.py` from its directory. Open its printed local URL. The server chooses a free loopback port and performs no telemetry collection on page load. **This host → Start monitoring** reads real counters; **Synthetic demo** uses labeled fixture data.

## Connect honest behavior to the interface

Keep sampling, fixed diagnostic commands, interpretations, job state, rendering, and export separable. Preserve command/time/status/exit-code/output provenance. Distinguish successful collection, an item requiring review, and incomplete coverage; do not present a decorative success state as system health.

Use interval CPU, available memory, explicit capacity semantics, and honest first/missing readings. Bound process enumeration, command time, output, and journal windows. Keep full command lines out of process views. Fixed allowlisted argv and local same-origin routes should not become arbitrary command/file endpoints.

Wire start/pause/resume, source selection, focused profiles, cancellation, expandable evidence, coverage, and JSON downloads to actual state. Keep demo/live labels and exports consistent. Pausing telemetry does not cancel a diagnostic job. A cancelled job must not execute remaining checks. Render external text with text content. Preserve responsive navigation, keyboard controls, and reduced-motion behavior.

Adapt the starter's views and thresholds to the request; its five profiles and visual theme are a starting implementation. Advanced drive-health interpretation, cgroup normalization, remote hosts, persistent history, and repairs are outside the implemented starter scope.

## Verify and retain evidence

From the copied app directory:

```sh
python3 -B scripts/run_checks.py --output <fresh-evidence-directory> --browser
```

This runs Python behavior/HTTP tests, JavaScript core assertions and syntax checks, then the real browser against an isolated local server using synthetic data. It records logs, commands, exits, screenshots, JSON downloads, HTTP outcomes, and source hashes. It does not execute the live host baseline by default. Missing browser tooling is a verification gap, never a browser pass.

When live inspection of the selected host is authorized, add `--live-host` to include real interval sampling, process population, and the five-command read-only baseline. This flag requires `--browser`; it is a distinct validation scope. The live route is also available manually in the application.

Inspect settled desktop and narrow screenshots after assertions pass. Compare expanded output and downloaded bytes to backend results. Exercise cancellation, reload, source locking, missing tools, and hostile text. Preserve material failures and rerun checks affected by a fix. The runner stops its owned test server and keeps an explicitly supplied local preview alive.

Keep fresh machine-specific output outside the shared skill. Bundled [example evidence](references/example-evidence/README.md) is historical illustrative data, not a current pass. [formats.json](assets/monitoring-app/objects/formats.json) describes snapshot, job, and export contracts.

## Deliver

Provide the verified local URL and starting control, source instructions, current manifest/evidence link, and coverage limits. Retain a requested live preview when supported and identify how to stop it. Record process/port identity only in task evidence. Browser viewport checks do not establish physical-device execution, fixture success does not establish live-host diagnosis, and this suite is not a hardware or security certification.
