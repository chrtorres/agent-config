# Capture comparison and resource disposition

## Routing decision

The requested workflow is safe, evidence-based work with Git repositories and GitHub collaboration: inspect repository state, preserve user changes, create focused commits, synchronize with remotes when authorized, and prepare or execute hosted collaboration artifacts.

| Candidate | Outcome | Inputs | Procedure | Resources | Validation | Score | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `verify-repository` | 0.25 | 0.50 | 0.25 | 0.25 | 0.25 | 28.75% | Related repository inspection, but does not cover Git history, change isolation, commits, remotes, or hosted collaboration; do not extend. |
| `skill-add` | 0.00 | 0.25 | 0.25 | 0.25 | 0.25 | 18.75% | General packaging procedure, not the requested Git/GitHub workflow; do not extend. |

The score uses the weighted rubric in `skill-add/references/skill-comparison.md`: outcome 25%, inputs 15%, procedure 35%, resources 15%, and validation 10%. No candidate reached the inclusive 75% extension threshold, so this is a new focused skill. The explicit user request for Git/GitHub work is preserved as the capture scope.

## User feedback and response

| Feedback | Response | Verification | Limit |
| --- | --- | --- | --- |
| User requested a reusable skill for “working with git/github.” | Created a provider-aware but credential-free procedure covering local Git state, safe edits, commits, remote synchronization, and GitHub collaboration. | Frontmatter, links, bundle index, and placeholder scan are validated during capture. | Live remote actions and hosted checks require an authorized target repository and account. |
| User requested a final review step requiring confirmation before a push, then asked to test the gate. | Added a mandatory final review containing destination, branch, commit range, changed files, checks, divergence, and push effect, followed by an explicit confirmation stop. | This task will validate the gate by stopping before push; the subsequent push remains pending confirmation. | The gate cannot be tested through a push until the user confirms the reviewed destination and commit range. |

## Resource disposition

| Resource category | Disposition |
| --- | --- |
| Procedure | Bundled in the canonical `SKILL.md`. |
| Scripts and tests | None required; the procedure uses standard Git commands and the host's optional GitHub client. |
| Fixtures and repository data | Excluded; no target repository or completed Git/GitHub artifact was supplied. |
| Git metadata and credentials | Excluded by design. Never capture `.git`, tokens, credential helpers, or private runtime state. |
| Fresh evidence | External task evidence only; do not store machine-specific diffs, identities, paths, or remote output in the shared skill. |
| External prerequisites | A target Git repository; Git; and, for hosted operations, an authorized GitHub account or equivalent service access. |

## Generalized values

Repository names, branch names, remote URLs, account and user identities, commit IDs, issue and pull-request numbers, local paths, hostnames, network addresses, service identifiers, credentials, and run-specific output are represented as discovered values or placeholders. No environment-specific values or secrets are bundled.
