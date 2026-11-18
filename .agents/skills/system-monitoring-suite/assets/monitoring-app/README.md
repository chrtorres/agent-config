# Fieldwork — system monitoring, first pass

A local Linux monitoring and troubleshooting dashboard that combines the read-only discipline of **system-health-diagnostic** with the working controls, visible tool evidence, responsive interface, and browser validation of **live-app-recreation**.

This is a portable starter copied from a shared skill into a task directory. Keep runtime state and fresh evidence in the task workspace.

## Run

Requires an existing Python 3.10+ installation and a modern browser. No Python packages, build step, Internet service, or account is required.

```sh
cd <app-directory>
python3 -B server.py
```

Open the local URL printed by the server. It binds only to `127.0.0.1` and chooses a free port. Use `--port <available-port>` for a stable port. Stop it with Ctrl+C. This is a manually launched process, not an installed background service.

Choose **This host → Start monitoring** for real observations. After the second sample, CPU shows the change between readings. Choose **Synthetic demo** for labeled fixture data without executing diagnostic commands on the host. **Take a quick tour** explains the workflow.

## What works

- Live CPU, available memory, swap occupancy, root capacity, uptime, load, and Linux pressure indicators. Sampling runs every three seconds while enabled. Pause stops browser sampling and keeps the last values. Resume continues the session.
- A session chart of up to 200 observations (about ten minutes with uninterrupted sampling). Missing CPU data remains missing; the first reading is not reported as zero.
- Up to 20 processes by resident memory, sampled from at most 2,000 process entries. Interval CPU uses one core as 100%. Parent PIDs are shown; environment variables and full command lines are not read.
- Five diagnostic profiles: baseline, startup/services, storage/thermals, recent errors, and packages/local network. Results expose the exact fixed command, timestamp, exit code, collection status, duration, output cap, and interpretation.
- One diagnostic job at a time, cancellation, explicit coverage gaps, and separate live/demo results. Commands have eight-second limits and retain at most 12 KB each. Cancelling terminates the current command's process group and prevents later checks.
- JSON download of retained samples, the latest snapshot/job, source labels, and coverage. Export is an explicit user action. The backend does not save diagnostic reports.
- Desktop and narrow-screen layouts, keyboard focus, a dismissible tour, and reduced-motion support. No remote fonts, analytics, scripts, or image assets.

Monitoring and diagnostics are independent: pausing telemetry does not cancel a diagnostic job. Use **Cancel check** to stop a job. Source switching is disabled while a check runs. Changing sources clears the current browser view and chart; a new job replaces the previous backend job. Reload clears the browser chart and restores the latest backend job with its source label. The backend keeps its last telemetry sample/counters briefly for interval calculation until process exit; it is not a durable history database.

## Interpretation and limits

This is the actual host-reading application, not a simulated operating system. Only **Synthetic demo** uses fixture data. The browser calls the Python backend over real loopback HTTP. It does not run an LLM or infer root causes.

Alert thresholds are triage heuristics: CPU ≥90% in an interval, memory ≥90%, root capacity ≥85%. A low sample does not certify system health. CPU and memory reflect host-visible `/proc`; cgroup/container limits are not normalized. Root filesystem usage excludes space reserved from ordinary users in its available-space denominator. Process counts can be incomplete because of races and permissions. Occupied swap does not establish active swapping.

Failed-unit and package-audit output is flagged for review. Successful collection of other command output means **Observed**, not a health pass. Missing tools, failed commands, capped output, and journal access restrictions mean **Limited**. **Unverified** coverage is never promoted to passing because a command was absent. Startup durations overlap and do not establish a critical path. Logs are capped at 40 visible entries per check from this boot and the last 15 minutes; journal filtering, retention, rate limiting, and permissions constrain interpretation.

The first pass does not inspect SMART/NVMe attributes, certify hardware, interpret vendor thermal limits, inspect graphics health, measure log growth, inspect previous boots, perform an update/security audit, persist long-term telemetry, or monitor remote hosts. Local interface counters and routes do not establish end-to-end connectivity. Empty `dpkg --audit` output checks installation state rather than package integrity or update currency.

Checks use existing access. There is no sudo, package installation or repository refresh, service change, cleanup, repair, reboot, SMART test, mount operation, stress test, remote network probe, or diagnostic upload. Unavailable checks remain explicit gaps.

The server exposes only explicit asset/API routes and fixed diagnostic profiles. Host/Origin checks and JSON-only POSTs protect against ordinary cross-origin requests and DNS rebinding. There is no arbitrary command or file endpoint, CORS, or external bind option. This is a local development tool: other processes/users with access to the same loopback port are inside its trust boundary. Do not forward the port to another machine.

## Source and combined workflow

- `monitor.py`: telemetry sampling, command allowlist, bounded execution, interpretation, jobs, and fixtures.
- `server.py`: loopback HTTP service and explicit routes.
- `web/`: buildless interface; `core.mjs` holds pure findings, coverage, chart paths, and export behavior.
- [WORKFLOW.md](WORKFLOW.md): how the two skill workflows map into this suite and how to extend it.
- `tests/`: behavioral, HTTP, and browser checks.
- `scripts/run_checks.py`: fresh evidence capture with command logs, exit codes, and source SHA-256 hashes.
- `--output` destination: task-local validation and screenshots. Synthetic exports are fixtures; live verification summaries omit raw logs and host identifiers.

## Validate

From this directory:

```sh
python3 -B -m unittest discover -s tests -v
node tests/test-core.mjs
node --check web/app.mjs
```

Python tests use synthetic process files, tiny subprocess fixtures, and real loopback HTTP; they do not run the real host diagnostic profiles. Browser tests default to deterministic demo checks through real loopback HTTP, and assert that no live telemetry or diagnostic request was made. Add `--live-host` only for authorized real-host sampling and the five-command live baseline. They save only a structured status summary of the live baseline; exported report fixtures and screenshots use demo data. The hostile-text browser case is intentionally injected fixture data.

Node is needed only for validation. Browser checks require an **existing** Chrome/Chromium executable and `playwright-core`; neither is installed by this project. Set `PLAYWRIGHT_MODULE` to the module's absolute entry point or resolvable module name if needed, and `BROWSER_EXECUTABLE` to the browser discovered on the host. The application itself has no Node dependency.

```sh
PLAYWRIGHT_MODULE=<existing-playwright-module> BROWSER_EXECUTABLE=<existing-browser> \
  python3 -B scripts/run_checks.py --output <new-evidence-directory> --browser
```

The runner starts and stops an isolated temporary server. The optional `--live-host` flag requires `--browser`. Evidence destinations inside a shared skill are rejected. To test a retained preview instead, add `--preview-url <printed-local-url>`. Each evidence directory must be new; failed results are retained. A browser pass covers this application in desktop and synthetic narrow viewports, not execution on a physical phone.
