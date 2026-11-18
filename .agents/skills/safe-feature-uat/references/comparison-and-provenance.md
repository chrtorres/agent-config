# Comparison and provenance guidance

## Routing decision for this skill

The completed workflow was compared with the plausible shared skills before creation:

| Candidate | Outcome | Coverage evidence | Score |
| --- | --- | --- | ---: |
| `verify-repository` | Related, below threshold | Outcome 0.5, scope 0.75, procedure 0.75, resources 0.75, validation 0.75 | 68.75% |
| `full-stack-app-creation` | Related, below threshold | Outcome 0.75, scope 0.5, procedure 0.5, resources 0.75, validation 0.75 | 62.5% |
| `live-app-recreation` | Related but different primary purpose | It emphasizes presenting a live recreation and fidelity limits; it does not provide the safe feature-copy and UAT handoff contract | Not scored |

The incoming workflow is therefore captured as the separate `safe-feature-uat` skill. It preserves the existing skills’ verification and browser-testing boundaries without broadening them. The scores use the five weighted dimensions in `skill-add/references/skill-comparison.md`; the inclusive 75% threshold was not reached.

## Feedback captured from the originating workflow

| Sanitized feedback | Response | Observed outcome | Remaining limit |
| --- | --- | --- | --- |
| “The page shows the button on this machine.” | Identify the live listener’s PID, executable/interpreter, working directory, and command line before comparing source. | The observed button was traced to a different implementation than the inspected Rust build. | A screenshot alone still cannot prove the source revision or device behavior. |
| “Launch a test window where I will assist.” | Launch the candidate on an available loopback port and provide a direct UAT entry point. | The candidate could be opened separately from the existing service. | The human must still exercise native authorization and visual behavior. |
| “The isolated v2 kept crashing; end debugging.” | Stop work, preserve the original implementation, and report the crash as a blocker rather than continuing unapproved changes. | No original `src` directory was changed. | A future run must capture crash stderr and perform incremental build checks before handing off. |

## Historical failure warning

The isolated `v2` experiment failed because a continuous loop in the candidate could crash the running application. Treat this as task feedback and an operational warning, not as a fresh reproduction or a claim that every loop is unsafe. Before handing a candidate to UAT:

- run it as a separately identifiable process with isolated runtime storage and a disposable port;
- inspect the loop’s exit, error, cancellation, and shutdown paths;
- exercise one bounded iteration or a controlled stop before enabling continuous operation;
- monitor the candidate process and retain stderr if it exits or takes down the test service;
- stop and remove the scratch candidate when the failure can affect the running app; do not continue UAT against it.

The UAT handoff must explicitly state whether continuous/live updates were tested. A candidate that crashes under its refresh loop is `fail` or `blocked`, never `pass`, even if its one-shot feature path works.

## Resource disposition

The workflow did not require bundling application source, binaries, credentials, device data, or dependency caches. Reusable resources are limited to this procedure and the UAT form. A future task should retain its own evidence manifest outside this skill with:

- source/build identifiers or hashes;
- discovered process identity and working directory;
- commands, ports, runtimes, and exit codes;
- screenshots, HTTP traces, logs, and test results;
- explicit authorization and device/service prerequisites.

Usernames, absolute paths, hostnames, ports, repository names, branch names, device identities, account IDs, credentials, tokens, and private runtime state are intentionally generalized or excluded. Synthetic values in the UAT template are placeholders, not live configuration.
