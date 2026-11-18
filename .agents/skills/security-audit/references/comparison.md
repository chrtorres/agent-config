# Capture provenance: security-audit

## Routing decision

The user explicitly requested a new skill named `security-audit`. The incoming workflow is a public-release privacy/security audit: inventory the full release surface, inspect data flow and packaging, remove or regenerate private evidence, rebuild the archive, and verify the application remains functional.

| Candidate | Outcome (25/15/35/15/10) | Score | Compatibility and evidence |
| --- | --- | ---: | --- |
| `system-monitoring-suite` | 0 / 0 / 0 / 0 / 0 | 0% | Builds and tests a Linux monitoring dashboard. It does not audit release privacy, secrets, or packaging and has a different deliverable. |
| `verify-repository` | 0.25 / 0.5 / 0.25 / 0.25 / 0.5 | 31.25% | Provides source/test verification and evidence discipline, but its outcome is repository-claim verification rather than release-data remediation. |
| `full-stack-app-creation` | 0.25 / 0.25 / 0.25 / 0.5 / 0.5 | 31.25% | Requires reproducible delivery and private-data exclusion as app-creation guidance, but does not provide a focused audit or scanner. |

All scores are below the 75% extension threshold, so this is a separate focused skill. It links conceptually to `verify-repository` and `full-stack-app-creation` without copying their application-building resources.

## Sanitized feedback and observed outcome

| Request/paraphrase | Response | Observed verification | Remaining limit |
| --- | --- | --- | --- |
| Audit a local storage app before open source and identify personal-data leakage. | Inspected source, runtime state, evidence, screenshots, packaging script, archive contents, and runtime data flow. | Found live scan evidence, username/hostname, mount paths, UUIDs, PIDs, and absolute paths in the release surface. | Pattern scans do not replace visual/media inspection. |
| Remediate immediately without changing the app. | Quarantined generated/private artifacts, changed packaging to an explicit source allowlist, updated ignore rules/docs, rebuilt the archive. | App smoke test, archive smoke test, backend tests, and clean text/archive scans passed. | Privileged live hardware validation remains private and must be regenerated outside a public tree. |
| Explain why the environment stopped working. | Identified removal of `node_modules` as a QA-environment regression, restored dependencies, and confirmed Python app behavior was unaffected. | `npm ls`, frontend core tests, backend tests, and server smoke test passed. | Full browser validation requires the external browser prerequisite and should write evidence outside the public tree. |
