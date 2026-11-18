# Diagnostic and interpretation contract

Use this when changing the collector, profiles, findings, or recommendations. These principles combine the diagnostic workflow with the app's actual first-pass coverage.

## Evidence and workload

Select the current host, symptoms, and authorized artifact destination. Start small. Use fixed local read-only commands and existing permissions; do not install host diagnostic packages, refresh repositories, restart services, repair, reboot, mount, scan the whole disk, stress memory, or initiate SMART/TRIM tests. Do not use sudo to obtain missing evidence. Building developer tooling in an isolated task directory is distinct from modifying the diagnostic host; follow the active task's dependency rules.

Capture UTC time, argv, collection status, exit code, elapsed time, truncation, and exact returned text. Retain bounded outputs only. The starter caps each command at eight seconds and 12,000 bytes, kills its process group on cancellation/timeout, and prevents later checks after cancellation. A denied/missing/inaccessible/timed-out/capped check is incomplete, not healthy.

## Resources and processes

- CPU is a delta of aggregate `/proc` counters; do not double-count guest time. The first sample is unknown. Compare load to logical CPU count; load includes runnable and uninterruptible tasks.
- Use `MemAvailable`, not free memory alone. Occupied swap is not active swapping. A single high interval is not sustained load or proof of a root cause.
- Root capacity is used divided by used plus space available to an ordinary user. Capacity and inodes are separate from physical drive health.
- Pressure is the `some avg10` share of time with stalled tasks. Missing pressure files remain unknown. Host-visible counters are not cgroup-normalized.
- Process CPU is measured between readings with one logical core as 100%. Reused PIDs require start-time identity; exited/inaccessible entries can be omitted. Read process names/parent IDs, not full command lines or environments.

The starter's thresholds (CPU 90%, memory 90%, root capacity 85%) are triage heuristics. Report them as such; they do not certify health.

## Focused investigation

| Area | Starter observation | Required interpretation / remaining coverage |
| --- | --- | --- |
| Services | System/user failed-unit output | Reported units need review; inspect the specific unit's context before attributing cause. |
| Boot | Boot timing and service durations | Durations overlap; blame output does not establish a critical path. |
| Storage | Capacity, root inodes, device layout | SMART/NVMe attributes and physical-drive health remain unverified. |
| Thermals | Optional existing `sensors` output | Warnings can coexist with valid readings. Vendor limits, trends, and GPU health remain unverified. |
| Logs | Current boot, last 15 minutes, at most 40 visible entries per check | Access, filtering, retention, rate limiting, and compression can hide events. No entries does not prove hardware health. |
| Packages | `dpkg --audit` | Installation state only, not installed-file integrity, updates, or a security audit. |
| Network | Local interface counters and routes | Cumulative drops do not measure current loss. Multiple routes can be valid. No remote connectivity test is implied. |

The starter deliberately omits previous-boot analysis, log-growth sampling, cached SMART interpretation, graphics diagnosis, update listings, and security configuration checks. Mark them unverified rather than implying broad coverage.

## Further investigation and repair verification

If deeper investigation is requested, add only checks that answer a concrete question and have reviewed resource impact. Bounded service logs or a short size delta can help distinguish a historical large log from an active flood; account for rotation/truncation. Cached drive-health properties need freshness and vendor-specific interpretation; an overall SMART pass can coexist with degraded attributes, and a historical test is not a new test. Never refresh or self-test implicitly.

For a user-applied fix, compare current service function, fresh errors, and short resource/log-growth observations against the prior evidence. Do not rerun the repair. Distinguish a recurring service failure from remaining per-file failures. Present the current operating condition, unresolved findings, and explicit gaps. Recommendations remain proposals.
