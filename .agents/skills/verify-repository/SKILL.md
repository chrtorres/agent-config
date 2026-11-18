---
name: verify-repository
description: Verify a repository's functionality, compatibility, and performance claims through source inspection and relevant isolated tests, and produce evidence for review before adoption or integration.
---

# Verify Repository Claims

Determine whether a repository delivers its claimed behavior in the user's intended environment. Distinguish documented promises, inspected implementation, observed execution, and measured results.

## Scope and inputs

Read applicable repository instructions. Identify the repository, claims to evaluate, intended use, target environment, and authorization boundary. Consult available context before asking for missing inputs; do not guess an unidentified project.

If the user requests verification before implementation, preserve the existing system and application configuration. Inspect setup scripts and documented side effects before running them. Use a scratch checkout and isolated dependencies where practical. Do not upload results or contact maintainers without authorization. A test request does not imply permission to deploy, modify production data, or replace system dependencies.

Discover paths, revisions, releases, hardware, software versions, and checksums at execution time. Keep environment-specific values in task evidence rather than embedding them in this reusable procedure.

## Inspect claims and implementation

1. Record the repository URL and exact commit. Read relevant instructions, documentation, release notes, build definitions, dependencies, tests, and implementation paths. Verify changing release and compatibility information against current primary sources.
2. Translate each material claim into observable behavior and the evidence needed to assess it. Resolve ambiguous terminology; a compatible interface, wrapper, or similarly named feature does not prove the underlying implementation is equivalent.
3. Separate shipped functionality from roadmap promises and inspected source from unavailable components. Describe the actual inspection scope accurately.
4. Identify whether existing tests exercise the claimed behavior. Utility tests, mocks, and successful builds do not alone prove end-to-end functionality. Choose checks that distinguish a working implementation from plausible failure modes.

For GPU or rendering projects, also read [references/gpu-verification.md](references/gpu-verification.md). For kernel modules, pre-driver firmware loaders, or hardware-unlock projects, additionally read [references/gpu-kernel-module-verification.md](references/gpu-kernel-module-verification.md).

## Prepare meaningful tests

Read relevant host, runtime, dependency, architecture, service, and hardware requirements without changing them. Select a source build, existing test suite, standalone test kit, or isolated reproduction according to the claim. Inspect release assets before choosing a platform package.

Record artifact URLs and hashes; compare SHA-256 with publisher checksums when available. A match confirms artifact identity against that value, not independent trust or correctness. Extract archives inside scratch storage and reject escaping paths.

Inspect executable setup and test launchers for configuration changes, external transfers, destructive cleanup, resource needs, and timeouts. Prefer the smallest representative test that supplies meaningful evidence. Expand testing when results or unresolved claims warrant it.

## Execute and interpret

- Retain commands, working directories, stdout, stderr, exit codes, settings, and expected outputs. Run sustained tests asynchronously and communicate progress.
- Verify individual outcomes and actual output files. A zero wrapper exit code or completion message is insufficient when child processes failed or reports were never generated.
- Classify outcomes as pass, fail, blocked, or not tested. A missing prerequisite blocks the affected test; it does not establish failure of the underlying algorithm or unsupported target hardware.
- Capture exact prerequisite errors and compare actual requirements with documented minimums. Avoid changing the host to bypass evaluation failures. A corrected package or isolated runtime can be tested within scope; otherwise report the blocker and next evidence needed.
- Keep correctness, compatibility, performance, and operational suitability separate. Reference-output agreement does not establish independent quality; synthetic timing does not establish application performance.
- For benchmarks, record inputs, workload, warm-up, sample method, units, resource use, and relevant configuration. Compare equivalent conditions, identify unavailable baselines, and avoid extrapolating vendor measurements to the user's environment.
- Respect deferred implementation boundaries. Successful isolated tests may justify a proposed application trial, but do not prove all integrations or deployments will work.

## Resources and evidence

Keep reusable helpers in `scripts/`, behavioral validation in `tests/`, domain guidance in `references/`, and output templates or fixtures in `assets/` when those resources are useful. Preserve supporting files when renaming or reorganizing the skill, and update relative references. Do not create empty scaffolding or copy project binaries, dependencies, or one-off review artifacts into the skill.

Store task-specific reports and raw evidence in the selected evidence directory. Include a machine-readable manifest and concise human-readable review covering:

- Repository URL, exact revision, selected release, artifact URLs, hashes, and checksum comparisons.
- Relevant target environment and inspection scope, including unavailable source.
- Claims reviewed, tests actually executed, outcomes, measurements with units, and precise blockers.
- Limitations, configuration changes if any were authorized, retained artifact locations, and next validation needed.

Lead with the verdict and a compact claim/result table where helpful. Link local evidence and cite primary sources for external claims. Do not describe blocked execution as proven functionality or seek adoption approval without the necessary evidence. When implementation is explicitly deferred, present the results for review and stop before integration.

## Reproduction bundle

Read [references/reproduction.md](references/reproduction.md) for the runnable fixture workflow, prerequisites and limits. [references/capture-provenance.md](references/capture-provenance.md) records resource disposition, comparison and user feedback. Reusable objects and report templates are in `assets/`; run `python3 -m unittest discover -s tests -v` from an isolated copy. Fresh run evidence belongs outside this shared skill.
