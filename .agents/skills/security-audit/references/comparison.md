# Capture provenance: security-audit

## Routing decision

The user explicitly requested extending the existing `security-audit` skill with a workflow for investigating credentials exposed in live process command lines. The incoming workflow is a runtime privacy/security check: inspect local process arguments without exposing values, classify active credentials as urgent, and trigger provider-side rotation/revocation while preserving redacted evidence.

| Candidate | Outcome (25/15/35/15/10) | Score | Compatibility and evidence |
| --- | --- | ---: | --- |
| `system-monitoring-suite` | 0 / 0 / 0 / 0 / 0 | 0% | Builds and tests a Linux monitoring dashboard. It does not audit release privacy, secrets, or packaging and has a different deliverable. |
| `verify-repository` | 0.25 / 0.5 / 0.25 / 0.25 / 0.5 | 31.25% | Provides source/test verification and evidence discipline, but its outcome is repository-claim verification rather than release-data remediation. |
| `full-stack-app-creation` | 0.25 / 0.25 / 0.25 / 0.5 / 0.5 | 31.25% | Requires reproducible delivery and private-data exclusion as app-creation guidance, but does not provide a focused audit or scanner. |

| `security-audit` (target) | 1 / 1 / 0.75 / 0.75 / 1 | 87.5% | Already audits secrets, private runtime state, evidence, and release surfaces. Before this update it lacked live `/proc` command-line inspection, redaction-safe process scanning, and explicit credential rotation guidance. |

The target score is above the 75% extension threshold, and the user explicitly requested this target. Extend `security-audit`; do not create a duplicate skill. The existing callers and release scanner remain unchanged, while the new process scanner and tests add the missing runtime check.

## Sanitized feedback and observed outcome

| Request/paraphrase | Response | Observed verification | Remaining limit |
| --- | --- | --- | --- |
| Audit a local storage app before open source and identify personal-data leakage. | Inspected source, runtime state, evidence, screenshots, packaging script, archive contents, and runtime data flow. | Found live scan evidence, username/hostname, mount paths, UUIDs, PIDs, and absolute paths in the release surface. | Pattern scans do not replace visual/media inspection. |
| Investigate whether an agent or tool exposed credentials in a process command line and make this a recurring audit check. | Added a redaction-safe Linux process scanner and explicit investigation, rotation/revocation, and evidence-handling guidance. | Synthetic process fixtures report only PID, executable, field, and category; the credential value is absent from findings and tests. | Non-Linux or permission-restricted process inspection must be reported as unavailable; provider-side rotation remains an external operational step. |
| Remediate immediately without changing the app. | Quarantined generated/private artifacts, changed packaging to an explicit source allowlist, updated ignore rules/docs, rebuilt the archive. | App smoke test, archive smoke test, backend tests, and clean text/archive scans passed. | Privileged live hardware validation remains private and must be regenerated outside a public tree. |
| Explain why the environment stopped working. | Identified removal of `node_modules` as a QA-environment regression, restored dependencies, and confirmed Python app behavior was unaffected. | `npm ls`, frontend core tests, backend tests, and server smoke test passed. | Full browser validation requires the external browser prerequisite and should write evidence outside the public tree. |
