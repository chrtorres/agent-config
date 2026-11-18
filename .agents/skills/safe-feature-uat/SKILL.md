---
name: safe-feature-uat
description: Test a feature safely in an isolated copy, compare the observed behavior with the reference implementation, and hand a runnable build to a human for structured UAT.
---

# Safe Feature Validation and UAT Handoff

Use this workflow when a user wants a feature investigated, ported, or experimentally changed without risking the working application. The result is an isolated, runnable candidate, evidence separating source claims from observed behavior, and concise instructions for a human acceptance test.

## Scope and safety boundary

Read applicable workspace instructions before touching files. Identify the reference application, target implementation, feature journey, supported environment, and authorization boundary. Preserve the working tree and running services unless the user explicitly authorizes changes. Do not run privileged, destructive, network-mutating, or production actions as part of ordinary validation.

Use a new scratch directory under the approved workspace. Give it a discoverable name such as `<project>-<feature>-test`; never overwrite an existing directory merely to recreate a test copy. Keep runtime state, ports, screenshots, logs, and reports outside the reusable source when practical. Discover paths, ports, executable versions, and process identities at runtime instead of assuming the foreground app is the one being inspected.

## Inspect the reference and target

1. Read repository instructions, launchers, build files, dependency locks, source paths, tests, and documentation for both the reference and target.
2. Translate the feature into observable behavior: entry point, controls, requests or commands, authorization prompts, progress states, success output, failure/cancellation behavior, persistence/session scope, and accessibility expectations.
3. Inspect the currently running service before attributing behavior to source. Identify the listening port, PID, executable or interpreter, working directory, command line, and source revision. A matching URL or title is not proof that the expected implementation is running.
4. Compare the reference behavior with the target implementation. Record missing UI controls, endpoint contracts, state ownership, permission boundaries, and compatibility assumptions before changing code.
5. Preserve user corrections as requirements. If the user supplies a screenshot or says a control is present, verify which process produced it and compare the rendered output with the target build.

## Build the isolated candidate

1. Copy only the internally consistent source and required tests/assets into the scratch directory. Exclude dependency caches, build outputs, credentials, runtime state, Git metadata, and unrelated sibling projects unless they are explicitly required and safe to reproduce.
2. Parameterize project paths, ports, hostnames, device identities, account IDs, and other environment-specific values. Never copy secrets, tokens, passwords, or private runtime data.
3. Implement the smallest vertical slice that exercises the requested feature. Keep authorization explicit and user initiated. For privileged local reads, keep the service unprivileged, place elevation behind the native system prompt, validate fixed executable paths and arguments, and distinguish retained measurements from retained authority.
4. Add focused tests for the feature contract, including the visible control, request/method/origin boundaries, concurrency or duplicate-action behavior, success state, cancellation/error state, and session or persistence semantics.
5. Build and launch the candidate on an available loopback port. If the candidate crashes, stop and capture the actual stderr, command, working directory, dependency versions, and exit code; do not infer success from a wrapper message.

## Verify behavior

Run checks in increasing cost:

- static/source inspection and formatting/lint checks;
- focused unit and contract tests;
- isolated HTTP or command tests using synthetic fixtures;
- browser testing of the actual control journey when a UI is involved;
- authorized live-device or external-service testing only when the user explicitly approves it and the required prompt/session is available.

For every step, record the command, working directory, configuration, exit code, expected result, actual result, and retained artifact. Inspect screenshots and returned data, not only status codes. Verify that the process serving the browser is the candidate process. Classify each check as pass, fail, blocked, or not tested. A permission-denied fixture proves error handling, not real hardware support; a successful build proves neither browser usability nor privileged integration.

Compare the candidate against the reference using an observable fidelity table:

| Journey point | Reference | Candidate | Evidence | Result |
| --- | --- | --- | --- | --- |
| Entry/control |  |  |  |  |
| Action/request |  |  |  |  |
| Progress/cancellation |  |  |  |  |
| Completion/output |  |  |  |  |
| Error/permission boundary |  |  |  |  |

Do not silently substitute a different implementation. If the feature cannot be tested because a dependency, browser, authorization agent, device, or external account is unavailable, report the exact blocker and the next evidence needed.

## Prepare the UAT handoff

Provide a short human test plan tied to observable outcomes. Include:

1. prerequisites and how to confirm the correct candidate process is running;
2. the exact local URL or launch command, using the discovered port only in task-local evidence;
3. numbered actions with expected visible results;
4. approval, cancellation, retry, duplicate-action, and error cases when applicable;
5. fields for the tester’s actual result, screenshot/log reference, pass/fail, and notes;
6. known limits, especially simulated versus live data and any authorization that was not exercised by automation.

Ask the human to report the first failing step and the visible message rather than only saying that the feature failed. Keep UAT feedback separate from engineering test results. After feedback, make only the requested scoped changes in the isolated copy, rerun affected checks, and refresh the UAT instructions.

## Reproduction resources

Use the target project’s source and tests as task resources, but do not copy the whole project into this skill. Retain a task-local manifest containing source identifiers or hashes, commands, prerequisites, artifacts, and outcome classifications. This skill provides the reusable UAT form at [assets/uat-report-template.md](assets/uat-report-template.md) and the comparison/resource guidance at [references/comparison-and-provenance.md](references/comparison-and-provenance.md).

## Delivery

Finish with the isolated candidate location or launch command, current validation result, UAT steps, evidence locations, and exact limitations. State whether the original application was changed (normally no). Generalize all reusable instructions; keep machine-specific paths, ports, usernames, hardware identifiers, screenshots containing personal data, and fresh logs in task evidence outside the shared skill.
