---
name: sanitize-code
description: Prepare a clean, reproducible code package by removing private and environment-specific dependencies, isolating sensitive runtime data, staging reviewed files, and verifying a fresh rebuild. Use for source-only handoffs, sanitized app templates, and reusable workflows derived from private projects.
---

# Sanitize code and verify a clean rebuild

Use this workflow to turn a working implementation into a reusable package. Preserve the agreed behavior and treat the user-provided input as a runtime dependency whenever the application can derive its own working data from it.

## Procedure

1. Define the deliverable and establish a behavioral baseline. Inventory authored source, dependency pins, public assets, generated files, user-provided data, evidence, archives, and runtime configuration. Trace sensitive values through command arguments, logs, caches, browser responses, exports, and working files. Record categories and locations without quoting the values.
2. Generalize identifiers and machine-specific paths through runtime discovery, configuration, or explicit inputs. Replace private example data with synthetic fixtures. Keep public prerequisites pinned or verifiable. If the app needs sensitive inputs, handle them through an appropriate local input channel and keep derived files in a restricted, session-scoped workspace. Check permissions, cleanup, caching and logging as applicable. A memory-backed workspace does not establish that host swap, browsers or crash collection retain nothing.
3. Stage a fresh package using a reviewed file allowlist. Include the dependency declarations, licenses, run instructions, and synthetic checks needed to reproduce behavior. Exclude private source files, derived assets, raw logs, screenshots, caches, and personal metadata. Do not delete existing originals or publish a package unless authorized.
4. Scan the staged package and inspect formats the scan cannot interpret. Use [security-audit](../security-audit/SKILL.md) when a broader release or runtime audit is needed. Treat a clean scan as limited evidence. Review the actual output archives or distribution trees when they are part of the delivery.
5. Build and run from an isolated copy with fresh working storage and the documented prerequisites. Use synthetic inputs for retained fixtures. When approved reference parity requires a private input, handle it transiently and record only aggregate results. Compare observable behavior and exercise cleanup after success and failure. Report pass counts, comparison coverage, and any prerequisite or privacy limit.

## Reproduction resources

- [Stage an explicit allowlist](scripts/stage_release.py) into a new directory. The helper copies reviewed files and preserves executable status while leaving out source file metadata such as timestamps.
- [Synthetic tests](tests/test_stage_release.py) exercise packaging, startup in a clean environment, excluded artifacts, and rejected paths.
- [Capture and resource disposition](references/capture.md) records the comparison, privacy decisions, and proof boundaries.

## Validation and delivery

From this skill directory, run `python3 -B -m unittest discover -s tests -v`. The standard-library workflow requires Python 3.10 or later. For a real project, supply a fresh destination and a UTF-8 JSON array of reviewed relative file paths.

```sh
python3 -B scripts/stage_release.py "<source-directory>" "<reviewed-allowlist.json>" "<new-package-directory>"
```

Keep fresh aggregate evidence outside the skill. Deliver the package with a reproducible launch command and state which identifiers were generalized, which inputs are supplied at runtime, and what was tested.
