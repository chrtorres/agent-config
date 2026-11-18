# Read-only checks and interpretation

Select checks supported by the host; missing tools are coverage gaps, not healthy results.

## Baseline and sampling

Use `uname -a`, `uptime`, `free -h`, `df -hT`, `df -i`, `/proc/pressure/{cpu,memory,io}`, and `vmstat 1 6`. The first vmstat row is an average since boot; interpret subsequent rows as interval samples. Load includes runnable and uninterruptible tasks and must be compared to logical CPU count. `ps %CPU` is a lifetime average; do not present it as current CPU use. Available memory and active swapping matter more than free RAM or occupied swap alone.

## Startup and services

Use `systemctl --failed`, `systemctl --user --failed`, `systemd-analyze` and bounded `systemd-analyze blame` output. Service durations overlap and are not additive; blame alone does not prove critical-path delay. Inspect a failed unit's bounded journal and its own build logs. Match error severity to current behavior. Check reboot-required markers and timestamps; never restart automatically.

## Storage and hardware

Use `lsblk`, `findmnt`, temperature sensors and kernel logs. Check current and available prior boots for I/O, filesystem, controller resets, OOM, machine-check and GPU errors. No matching log entries does not prove hardware health. Do not run fsck on mounted filesystems.

Prefer already-available SMART reports via `smartctl -a` if accessible, or cached UDisks properties. For UDisks, first run `udisksctl info -b /dev/sda`, read its Drive object, then use `udisksctl info -p drives/EXACT_OBJECT_NAME`. `-d` expects a UDisks drive identifier, not `/dev/sda`. Do not invoke refresh/self-test methods. Record cache freshness, overall status, bad-sector count, failing attributes and self-test history separately. SMART passing can coexist with degraded attributes. SSD attributes may be vendor-specific; a summarized bad-sector count needs detailed interpretation before asserting failure. Missing NVMe health fields are unknown, not a pass. A reported successful historical self-test is not a new test.

Check `sensors` and `nvidia-smi` if installed. Sensor-read warnings can coexist with valid CPU sensor readings. No GPU ECC support is not an ECC pass. Note thermal trends and limits when available rather than declaring every temperature universally safe.

## Logs and packages

Use journal counts over explicit windows, bounded tails, file metadata and a 5–10 second size delta. Account for rotations, truncation, rate limiting and repeated-message compression. Large historical logs and an active flood are separate findings. Inspect rotation configuration without invoking logrotate. Summarize private filenames rather than reproducing them unnecessarily.

Use `dpkg --audit`, cached `apt list --upgradable`, existing maintenance logs/timers and reboot markers. State that cached update listings are not a current security audit. Do not run apt update, upgrades, refresh, vacuum, cleanup or reset. A clean dpkg audit checks installation state, not every installed file's integrity.

## Network and security context

Use `ip -br address`, `ip route`, `ip -s link`, `resolvectl status`, and `ss -lntu`. Snapshot drop counters do not establish current packet-loss rate; compare samples if relevant. Multiple default routes can be valid when metrics differ. Local configuration does not establish end-to-end connectivity. Do not contact remote services for local-only requests. Report Secure Boot and kernel mitigation state as observations; avoid treating configuration choices as a security certification or a cause of slowness without evidence.

## Completion

Cover CPU, memory, capacity, storage health availability, thermal/graphics indicators, services/startup, recent errors, installation/update state and local networking. Mark each as observed, problematic or unverified. Give a finite report rather than repeatedly sampling after the evidence is stable.
