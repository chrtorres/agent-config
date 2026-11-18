---
name: system-health-diagnostic
description: Diagnose Ubuntu or Linux system health and startup slowness using local read-only observations; verify fixes and report evidence, remaining faults, and diagnostic limits without performing repairs.
---

# System health diagnostic

Use for live Linux health checks, startup slowdown investigations, and verification after user-applied fixes. Default to local tools only. Creating this skill does not authorize repairs or diagnostic execution on another host.

## Scope and boundaries

Use existing tools and permissions. Do not install packages, refresh repositories, reset indexes, truncate or rotate logs, change services or settings, mount filesystems, reboot, trigger SMART tests or TRIM, or run repair commands. Do not use sudo to gain additional access without authorization. Explain inaccessible checks and continue independent work. Even read-only workloads can affect responsiveness: avoid full-disk scans, broad checksum sweeps, stress tests, or memory tests unless separately requested and their effects reviewed.

Report to the conversation by default. Saving raw output requires an authorized artifact destination; logs can contain filenames, addresses and other private information. Do not upload diagnostic data.

## Procedure

1. Confirm the host, symptoms, uptime and current authorization. Read repository instructions if working in a managed workspace. Start with a small baseline; use the optional `python3 scripts/collect_health.py` to emit bounded JSON to stdout without creating a report file.
2. Follow [references/checks.md](references/checks.md) for resource sampling, boot/services, storage, hardware, graphics, packages and networking. Batch independent observations. Record unavailable tools, permission failures, timestamps and command exit codes.
3. Investigate active anomalies with bounded samples. Count repeated errors by message and time window; compare log sizes over a short interval. Identify process ancestry without exposing full command lines that may carry secrets. Inspect specific service logs and build failures before attributing a cause.
4. If verifying a repair, establish the current service state, functional completion, fresh errors and short resource/log-growth samples. Never rerun the repair automatically. Distinguish remaining per-file failures from a recurring service failure.
5. Report the present operating condition first, then prioritized unresolved findings and explicit coverage limits. Use [assets/report-template.md](assets/report-template.md) as a guide, not a required verbosity target. Recommendations are proposals, not execution authorization. Do not call a live inspection a complete hardware certification.

Read [references/case-study.md](references/case-study.md) only when investigating a Tracker indexer/logging storm. Its historical repair commands are context, not an executable remediation workflow.

## Package verification

Run `python3 -B -m unittest discover -s tests -v` from this directory after editing the collector. Tests use mocked commands and do not diagnose a live host. `objects/collection-format.json` documents the collector output contract. Keep generated host-specific evidence out of the reusable package.
