# Architecture, visual implementation, and QA

## Creation decisions

The smallest implementation that can read Linux host state needs a local backend. The starter uses Python's standard library for HTTP, sampling, and fixed subprocess checks; buildless HTML/CSS/ES modules provide the dashboard. Browser-local functions alone cannot establish genuine host integration. No model or hosted service is part of this application.

`monitor.py` separates sampling, interpretation, allowlisted argv, jobs, and fixtures. `server.py` serves only explicit assets and API routes on IPv4 loopback. `web/core.mjs` owns pure findings, coverage, chart paths, and report construction; `web/app.mjs` wires actual HTTP responses to controls. `objects/formats.json` defines field contracts. Preserve those imports/layout when copying.

The interface takes its sage/ivory theme, visible activity, expandable tool evidence, guided/manual paths, and responsive behavior from the live-app workflow. It is a new dashboard, not an operating-system recreation. Retain source and honest scope labels beneath the presentation.

## Observable behavior

| Control/state | Evidence that establishes behavior |
| --- | --- |
| Initial page | HTTP success; unknown counters; no telemetry/diagnostic request on load |
| Start/pause/resume | Source-labeled responses; sample count advances, stops for a full poll period, then advances again |
| Chart | Actual retained samples, missing values preserved, timestamps reflected in horizontal spacing |
| Process view | Returned process data rendered as text; interval CPU and parent PIDs |
| Profile | One job, exact allowlisted checks, progress tied to returned results |
| Expanded result | Command/time/status/exit/duration/truncation and output agree with backend data |
| Cancel | Active command ends; later checks remain unrun; observed evidence is retained |
| Source switch | Disabled while a job runs; chart/display clears on change; labels and exports match the selected source |
| Reload | Chart clears; latest backend job restores with its correct source; monitoring stays stopped |
| Export | Actual JSON download preserves the displayed job/output and source |
| Coverage | Unrun/inaccessible/excluded areas stay unverified; collection success is not a hardware pass |
| Narrow/keyboard view | Essential navigation fits, no page overflow, tour dismisses with Escape, focus is visible |

Use settled screenshots alongside assertions. The original screenshot review led to stronger supporting-copy contrast and tighter mobile navigation; those fixes are included. A full-width passing assertion alone cannot reveal illegible copy or a visually clipped control.

## Boundary and race checks

Keep shell execution, arbitrary argv/files, remote bind options, full process command lines, and cross-origin access out of the server. The starter checks Host/Origin/fetch-site and JSON POST bodies, keeps command output bounded, and distinguishes timeout/missing/access restriction from observed results. Loopback is a local-process trust boundary, not an authentication system for hostile users on the same machine. Do not forward its port.

Test cancellation before launch and after a command closes stdout, PID reuse, missing `/proc`, journal restrictions, capped output, and overlapping jobs. The frontend ignores stale source results, preserves unknowns, and renders untrusted process/tool text without HTML interpolation.

## Validation sequence

1. Copy the starter outside the skill. Check prerequisites without altering the diagnostic host. Keep evidence in a fresh external destination.
2. Run package-creation tests if changing the scaffold helper. Run the generated app's Python tests (synthetic process files, tiny command fixtures, actual loopback HTTP), JavaScript core tests, and syntax check.
3. Run the browser checker through the copied app's runner. Default QA uses real loopback networking with synthetic telemetry/checks and asserts it made no live requests. With authorized host scope, `--live-host` additionally exercises real sampling/process data and the five-check live baseline. Neither scope borrows another run's results.
4. Inspect expanded evidence and JSON bytes, then representative desktop and narrow screenshots. Keep failed artifacts that explain material fixes; rerun affected checks.
5. Verify source hashes and command exits in the manifest. Report actual runtime versions and browser scope. Keep current evidence external; curated examples inside the skill are illustrative.

Keep source hashing scoped to authored root files and source directories. During capture, a recursive basename match accidentally included a dependency's README; the bundled regression test checks that dependency trees and generated evidence stay outside the source manifest.

An owned temporary preview is stopped by the runner. A supplied preview is left running and must be a dedicated, idle local test session. Handoff of an actual requested live application may retain a separate preview, with its real process/URL recorded only in task evidence. Follow the active environment's browser/preview rules; unavailable infrastructure is a coverage gap.
