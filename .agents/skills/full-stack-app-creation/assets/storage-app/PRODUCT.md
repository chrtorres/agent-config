# Storage telemetry product brief

Atlas is a local Linux storage dashboard for an owner deciding which volume needs attention and where capacity is available. Start with a live overview, compare drives, inspect a drive's partitions and mounted filesystems, review capacity or health findings, then export the current evidence.

## Delivery and architecture

- Local, loopback-only Python 3.10+ HTTP service; buildless HTML/CSS/JavaScript frontend. Physical device access requires a local collector, so cloud hosting cannot provide this integration.
- Structured `lsblk` inventory replaces the reference script's display-only parsing. `statvfs` supplies exact mounted usage, `/proc/diskstats` supplies interval I/O, and optional `smartctl --json --all` provides health when permitted. Never run installation suggestions. The ordinary collector stays unprivileged; an explicit same-origin scan action can invoke fixed SMART queries through native polkit authentication.
- SQLite stores a bounded history of 720 snapshots in task-local runtime storage. Fresh samples are cached for two seconds. Browser refresh is every ten seconds and can be paused. Demo data is explicitly labeled and never enters live history.
- APIs: GET `/api/snapshot?source=live|demo`, `/api/history?source=live|demo`, `/api/export?source=live|demo`, `/api/health`. No device mutation endpoints. The browser persists source, units, active view, and update preference locally.
- Overview, drives, volumes, activity, and health views; searchable/sortable volumes, unmounted visibility, drive detail dialog, JSON download, local history. Clear loading, empty, partial, stale, and error states.
- Filesystem totals deduplicate mounted filesystem identities. Used / available / reserved are separate. Unmounted capacity has unknown usage, not free space. Physical capacity and mounted filesystem capacity have different denominators. Shared filesystems are not attributed repeatedly to individual drives.
- Local-only trust boundary: fixed argument lists, timeouts, no shell execution, safe DOM text, loopback binding, Host validation, no cross-origin API access, restrictive CSP. Health is unknown when unavailable, never inferred from capacity.
- First-pass exclusions: file deletion, mounting/formatting, directory scanning, predictions without sufficient history, background daemon installation, remote fleet management, cloud publication, and human SUS survey results.

## Acceptance rubric (declared before implementation)

Each scenario is worth five points, awarded only when its assertions pass. Minimum acceptance is **95/100**, every critical scenario must pass, and no serious/critical automated accessibility violations or uncaught browser errors are permitted. This is an engineering acceptance score, not a measured human satisfaction score.

| ID | Scenario | Critical |
| --- | --- | --- |
| A01 | Live inventory matches real lsblk devices through HTTP | Yes |
| A02 | Filesystem accounting balances and deduplicates mounts | Yes |
| A03 | Unmounted partitions retain unknown usage and swap is distinct | Yes |
| A04 | SMART missing, denied, failing and healthy states remain truthful | Yes |
| A05 | I/O uses interval deltas with reset and first-sample handling | Yes |
| A06 | Snapshot history persists through service restart and stays bounded | Yes |
| A07 | API validates inputs, rejects unsafe hosts and exposes no mutation | Yes |
| A08 | Overview metrics and visualization agree with returned bytes | Yes |
| A09 | All five navigation views render their actual data | No |
| A10 | Drive dialog shows partitions, usage and coverage | No |
| A11 | Volume search, sort and filter change the shown results | No |
| A12 | Refresh, pause and resume work without overlapping requests | Yes |
| A13 | Unit/source preferences survive reload; demo stays separate | Yes |
| A14 | Downloaded JSON matches current source and data | Yes |
| A15 | Capacity findings use declared 80% warning / 90% critical thresholds | Yes |
| A16 | Empty, partial and malformed collector results are handled | Yes |
| A17 | Network errors show stale data and retry recovers | Yes |
| A18 | Desktop and mobile layouts have no page overflow | No |
| A19 | Keyboard dialog, focus and automated accessibility checks pass | Yes |
| A20 | Live integration, reproducible commands, screenshots and source hashes retained | Yes |

Usability context: [ISO 9241-11](https://www.iso.org/standard/63500.html) describes usability in context; [MeasuringU's SUS research](https://measuringu.com/sus/) reports a historical average of 68 for the human questionnaire. Automated tests cannot supply a valid SUS score. Human usability remains unmeasured in this one-shot delivery.
