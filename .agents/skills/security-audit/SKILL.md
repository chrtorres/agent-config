---
name: security-audit
description: Audit an application source tree and release artifacts for secrets, personal data, private runtime state, and unsafe packaging before open-source or public distribution; remediate generated evidence without changing application behavior and verify the clean release.
---

# Security audit for public release

Audit the complete source-and-delivery surface of an application before publishing it. Treat generated evidence, screenshots, logs, databases, archives, caches, and dependency trees as shippable unless the release process explicitly excludes them. The objective is a clean, reproducible release with no secrets or machine-specific personal data, while preserving application behavior.

## Procedure

1. Read workspace instructions and identify the application root, release command, packaging scripts, runtime entrypoint, tests, generated-artifact directories, and intended public distribution format. If the project is not under version control, treat every present file as potentially shippable.
2. Inventory source, hidden files, runtime state, evidence, screenshots, archives, databases, bytecode, dependency trees, and packaging manifests. Inspect both the working tree and any prebuilt archive.
3. Search text and serialized data for secrets and personal/system identity: credentials and tokens, private keys, email/phone data, usernames, home paths, hostnames, PIDs, absolute working directories, device serials/UUIDs, mount paths and labels, IP/MAC addresses, browser profiles, timestamps tied to a real user, and raw diagnostic output. Inspect image/document metadata and rendered screenshots when they may contain identity.
4. Trace data flow in the application. Identify what is collected, persisted, exported, logged, rendered, or sent externally. Distinguish local diagnostic data intentionally exposed to the owner from accidental data embedded in the public release. Check whether exports and evidence include the full live snapshot.
5. Inspect packaging logic for unsafe inclusion rules such as “all files in evidence,” recursive directory copies, runtime directories, dependency trees, or live validation output. Replace broad inclusion with an explicit authored-source allowlist and clearly labeled synthetic fixtures. Generalize environment-derived values; never embed secrets or tokens.
6. Remediate only the release surface unless the user requests a behavior change: quarantine or remove live/private artifacts, regenerate evidence from synthetic fixtures, update ignore rules and documentation, and make packaging exclude private/generated state by construction. Preserve the app's APIs, UI, runtime behavior, and tests.
7. Rebuild the release archive in an isolated output location. Inspect archive members and payload contents, then run the smallest real application smoke test from the extracted archive. Run relevant unit/backend/frontend tests without retaining live evidence in the public tree.
8. Report findings by severity with exact paths and evidence, state what was changed, distinguish recoverable quarantine from deletion, and disclose remaining limits. Do not claim that local-only runtime collection is equivalent to zero sensitive data; document local inventory and export semantics.

## Reproduction resources

- [`scripts/audit_release.py`](scripts/audit_release.py) scans a source tree and optional archive for common secret, identity, and private-runtime patterns without printing matched values.
- [`tests/test_audit_release.py`](tests/test_audit_release.py) exercises tree scanning, archive scanning, safe synthetic data, and nonzero findings.
- [`references/comparison.md`](references/comparison.md) records the candidate-skill comparison and routing decision for this capture.
- [`references/resource-disposition.md`](references/resource-disposition.md) records what was inspected, bundled, regenerated, generalized, quarantined, or excluded.

The scanner uses only the Python standard library. It is a complement to source review, packaging inspection, and screenshot/document inspection; a clean pattern scan is not proof that rendered or encoded media contains no personal data. Use a fresh temporary evidence directory for validation. Keep real hostnames, usernames, paths, device identities, raw logs, screenshots, archives, credentials, and runtime databases outside this skill.

## Validation and delivery

From this skill directory:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/audit_release.py --root <application-root> --archive <release-archive>
```

The audit command exits nonzero when it finds configured sensitive patterns and reports only file/member, line, and category. Validate the actual extracted release with its documented startup command and a representative local request or user journey. Confirm that expected synthetic fixtures remain available, private artifacts are absent, and application tests still pass. Store fresh machine-specific reports outside the shared skill.

Link this canonical directory into each intended model discovery directory with the `skill-add` linker. The invocation name is `security-audit`. Required external inputs are the application source and its release/validation instructions; no external account, credential, network service, or privileged access is required for the audit itself.
