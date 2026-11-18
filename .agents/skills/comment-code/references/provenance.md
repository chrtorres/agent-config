# Workflow provenance and resource disposition

## Origin

This skill generalizes a completed review of an existing local storage-telemetry application. The task asked for human-readable comments wherever code could be misconstrued, with behavior preserved and verification performed. The captured method is intentionally domain-neutral.

## Candidate comparison

The incoming workflow was compared against the accessible canonical skills before creation. The score uses the skill-add weighted rubric; it measures coverage of the incoming commenting workflow, not text similarity.

| Candidate | Outcome 25% | Scope 15% | Procedure 35% | Resources 15% | Validation 10% | Total | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `verify-repository` | 0.25 | 0.50 | 0.50 | 0.25 | 0.75 | 42.50% | Related verification workflow; not a commenting deliverable |
| `full-stack-app-creation` | 0.25 | 0.50 | 0.25 | 0.25 | 0.50 | 31.25% | Builds applications; comments are incidental |
| `skill-add` | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 | 25.00% | Packages workflows; does not review source comments |

All candidates are below 75%, so this is a separate focused skill. The user's requested target name, `comment-code`, is also preserved.

## Resource disposition

| Resource category | Disposition |
| --- | --- |
| General commenting method | Bundled in `SKILL.md` |
| Review criteria and anti-noise rules | Bundled in `references/comment-checklist.md` |
| Comparison, feedback, and provenance | Bundled here with generalized paths |
| Target application source and tests | Deliberately excluded; the method must apply to a future target |
| Dependency trees, caches, generated evidence, screenshots, runtime state | Deliberately excluded; discover or regenerate from the target project |
| Secrets, tokens, hostnames, device identities, private paths | Excluded and not required |

## Feedback and observed outcome

| Sanitized request | Response | Observation | Limit |
| --- | --- | --- | --- |
| Comment code that may be misunderstood, continuing until the confusing areas are covered | Added comments around semantic accounting, deduplication, SMART status, authorization, caching, request races, and validation boundaries | Focused tests and the full application validator passed at 100/100 in the source task | Human maintainability review remains contextual; no comment set can prove every future reader's interpretation |

The original task's absolute workspace paths and runtime evidence are not prerequisites for reproducing this skill.
