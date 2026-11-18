# Decide whether to extend or create

Perform this comparison after inventorying the completed workflow and before assembling its shared resources. It prevents duplicate skills while keeping independently useful workflows discoverable.

## Inspect plausible candidates

Search the canonical skill catalog and any user-named targets. Read descriptions to shortlist relevant candidates, then read their actual procedure, applicable supporting resources, prerequisites, and callers. Resolve discovery symlinks so multiple model links to the same canonical skill count as one candidate. Do not inspect unrelated installed skills merely to fill a quota. If nothing plausible exists, record the search scope and create a new focused skill without fabricating a comparison percentage.

Compare the completed reusable method, including the user's corrections, rather than a transcript or the volume of generated files. Exclude generic boilerplate such as reading workspace instructions or writing a final answer. Similar technology alone is weak evidence: two Python applications can solve unrelated problems. Conversely, a domain-specific worked example can substantially duplicate a general app-creation procedure despite different filenames and content.

## Weighted duplication score

For each candidate, assess how much of the incoming workflow's meaningful requirements and method the existing skill already covers **before this update**. The denominator is the incoming workflow, not the size of the existing skill. Do not count planned additions as preexisting coverage.

| Dimension | Weight | What constitutes coverage |
| --- | ---: | --- |
| Intended outcome and user journey | 25 | Same problem, deliverable, and success path |
| Invocation scope and inputs | 15 | Same triggering requests and material input contracts |
| Essential procedure and decisions | 35 | Existing steps and decision rules accomplish the incoming method |
| Reproduction resources and dependencies | 15 | Existing code, fixtures, formats, or tools directly support the method |
| Validation and acceptance | 10 | Existing checks establish the required observable outcomes |

Assign a coverage factor of 0, 0.25, 0.5, 0.75, or 1 to each dimension: none, limited, partial, substantial, or complete coverage. Cite concrete steps, resources, or missing behavior for each factor. Where a factor is uncertain, inspect further and record the uncertainty; do not resolve uncertainty by assuming full coverage. All dimensions apply; missing candidate support scores zero rather than disappearing from the denominator.

`duplication percentage = sum(dimension weight × coverage factor)`

Use the unrounded result for the decision. This is a documented judgment rubric, not a text-similarity algorithm, statistical confidence measure, or industry standard. Do not change weights, fragment tasks, or count boilerplate to push a preferred decision across the threshold.

## Apply the 75% threshold

- **Score ≥75% and compatible scope:** extend the existing canonical skill. Preserve current callers and working resources. Add the novel method, feedback, tests, or a linked optional example; avoid copying an entire sibling skill. An already complete match may need only a documented no-change decision or a small evidence/feedback addition.
- **Score <75%:** create a new focused skill. Related material may be linked or reused through a supported dependency, but do not duplicate large resource trees. Bundle the dependency closure or explicitly document its external prerequisite so the new skill remains reproducible.
- **High score with incompatible scope or trust boundaries:** do not broaden permissions or silently change invocation behavior. Record why a safe extension cannot preserve both contracts; separate the independently useful portion or use a clearly isolated optional mode with its own prerequisites. Explain the exception to the numerical routing rule.
- **Several qualifying candidates:** select the compatible candidate with the highest score; break ties by the closest intended outcome and least scope expansion. Do not modify all candidates merely because they share generic steps.
- **Unavailable candidate resources:** mark comparison incomplete, continue inspecting accessible alternatives, and do not claim a percentage or overwrite that candidate without evidence. State any resulting capture limitation.

Honor explicit user instructions about extending a particular target or creating a separate skill. Record that direction alongside the comparison instead of adjusting the score to disguise an override.

## Retain a reviewable decision

Record a compact table with candidate skill name, evidence references, five coverage factors, calculated percentage, compatibility, chosen action, and the new material's destination. Preserve competing plausible candidates and the reason for rejecting them. Include what remains unchanged so future maintainers can assess caller compatibility. Generalize environment-derived locations in shared provenance; actual paths and fresh execution identities belong in task-local evidence.

For each relevant feedback item, record: sanitized user request or paraphrase → change made → observed outcome/test → remaining limit. For example, a request for session-persistent access may be satisfied by timestamped results while authorization remains per operation; record that distinction rather than claiming cached credentials. Historical feedback never grants fresh privileges.

### Synthetic boundary examples

All factors below describe fictional comparisons, not measured scores for an installed skill.

| Case | Factors in dimension order | Score | Decision |
| --- | --- | ---: | --- |
| Related but below threshold | 1, 1, 0.5, 0.75, 0.5 | 73.75% | Separate focused skill; reuse supported related material |
| Exact threshold | 0.75, 0.75, 0.75, 0.75, 0.75 | 75% | Extend when scope is compatible |
| Strong match | 1, 1, 0.75, 0.75, 1 | 87.5% | Extend; capture the specific missing decisions/resources |
| Superficial technology match | 0, 0.25, 0.25, 0.5, 0.25 | 22.5% | Separate skill |

After routing, follow the normal resource capture, isolated validation, indexing and discovery-link procedure. The comparison itself neither validates the implementation nor authorizes repeating privileged actions.
