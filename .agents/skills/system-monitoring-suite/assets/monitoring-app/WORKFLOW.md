# Combined workflow: observe, inspect, retain

This portable starter combines two methods. Keep task state and host evidence in the copied application workspace; the shared bundle is the reusable source.

## Establish the session

1. Identify the Linux host and symptom. The dashboard shows the host identity after **Start monitoring**. In a different environment, confirm that the host running Python is the machine being investigated; a browser's location does not select the diagnostic target.
2. Start with resource sampling and a baseline. Use existing permissions and installed tools. Treat CPU as an interval measurement and occupied swap as occupancy, not swapping activity.
3. Choose a focused profile based on observations. Record inaccessible checks as coverage gaps. A test using **Synthetic demo** exercises controls and rendering; it cannot diagnose the machine.

## Inspect before deciding

1. Expand relevant command evidence. Match the category, collection time, status, exit code, bounded output, and current symptom before proposing a cause.
2. Separate three concepts: successful collection, a reported item that needs review, and unverified coverage. Neither a green interface accent nor successful command execution is a system-health certification.
3. Use the coverage view to decide what independent evidence is still needed. Deeper investigation can follow the original diagnostic skill's read-only references, but this first-pass app deliberately exposes only its fixed command profiles.
4. Propose next steps from the evidence. A service failure needs that service's specific context; overlapping boot durations alone do not prove a delay. Do not turn a recommendation into an automatic repair. For verification after a user-applied repair, run the appropriate profile again and compare explicit exports; do not rerun the repair.

## Retain and validate

1. Export only when retaining diagnostic data is intended. Raw logs can contain private paths and addresses. The app does not upload evidence.
2. Verify the real core, the HTTP boundary, and browser controls separately. Use small fixtures for unknown counters, truncated output, missing commands, cancellation, PID reuse, and untrusted text. Use actual HTTP responses when claiming backend integration.
3. Inspect screenshots after assertions pass. Check desktop and narrow layouts, legible results, honest source/status labeling, and essential controls. A screenshot is not a substitute for a working action.
4. Tie commands, results, and screenshots to source hashes in a fresh manifest. Keep live summaries distinct from synthetic exports. Recheck source affected by a fix, and retain material failure evidence.

## Fidelity map

| Source behavior or principle | First-pass implementation | Meaningful limit / evidence |
| --- | --- | --- |
| Read-only Linux baseline | Fixed local command profiles and `/proc` sampling | Current host and existing permissions only; HTTP/live-baseline test |
| Bounded anomaly investigation | Threshold findings, failed-unit review, capped recent journals | Triage rules, no root-cause engine or active log-growth sample |
| Storage and hardware coverage | Root capacity, inodes, device layout, optional `sensors` output | SMART/NVMe, graphics, and thermal interpretation explicitly unverified |
| Visible real tool execution | Expandable exact command results with time/status/exit code | Actual Python execution in live mode; labeled fixtures in demo mode |
| Working interaction beneath graphics | Start/pause/resume, profile execution/cancel, views, report downloads | No repair/mutation controls or simulated approvals |
| Session retention | Browser chart and backend latest job in memory; explicit JSON download | No durable monitoring database; reload behavior is documented/tested |
| Guided live view | Responsive dashboard, three-step tour, manual controls | New application inspired by the live-app method, not an OS emulator |
| Observable delivery | Local server, browser outcome assertions, screenshots, hash manifest | Browser viewport checks do not establish physical-device compatibility |

## Extending the suite

Add a diagnostic only when it answers a concrete question and its resource impact is bounded. Keep argv fixed in the backend; do not accept shell strings, caller-supplied command arguments, arbitrary paths, or mutation actions. Define what an empty/nonzero/restricted/truncated result means, preserve exact provenance, and expose remaining uncertainty. Add tests for meaningful failure states and drive any new controls in the browser.

Longer-term history, cgroup-aware metrics, per-service journal investigation, cached drive-health inspection, and post-repair comparisons are possible follow-ups. They are outside this first-pass implementation and should receive their own scope and validation.
