# Capture provenance and comparison

## Completed workflow represented

The source workflow converted a request for an immersive 3D viewer refinement into a Markdown user story. It recorded the requested interaction, preserved a View-Only boundary, separated current acceptance criteria from future editable-dimension plans, and made no application implementation changes. A later, separately requested repository-hygiene action added the exact document filename to the applicable `.gitignore` after repository discovery.

## Comparison decision

| Candidate | Outcome coverage | Input/scope coverage | Procedure coverage | Resource coverage | Validation coverage | Score | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `full-stack-app-creation` | 0.25 × 25 = 6.25 | 0.25 × 15 = 3.75 | 0.25 × 35 = 8.75 | 0 × 15 = 0 | 0.25 × 10 = 2.5 | 21.25% | Related but below threshold; create a separate focused skill |
| `git-github-workflow` | 0 × 25 = 0 | 0.25 × 15 = 3.75 | 0.25 × 35 = 8.75 | 0 × 15 = 0 | 0.25 × 10 = 2.5 | 15% | Supports optional repository hygiene only; do not extend |

`full-stack-app-creation` covers product-definition work as one stage of building a complete application, but its required outcome includes architecture, implementation, browser testing, and delivery. The incoming workflow ends at a scoped planning document and intentionally excludes implementation. `git-github-workflow` covers repository inspection and safe Git changes, but not user-story definition. Both are related prerequisites or optional companions, not compatible replacements.

## Resource disposition

| Resource | Disposition | Reason |
| --- | --- | --- |
| User-story Markdown structure | Bundled in `SKILL.md` | Small, portable, and central to the workflow |
| Original product request and route names | Generalized | Task-specific content belongs to the task document, not the reusable skill |
| Application source and 3D assets | Excluded | No implementation or asset inspection is required |
| Git repository identity and paths | Discovered at use time | Environment-specific values must not be hardcoded |
| Credentials, caches, generated runtime state | Excluded | Not required and not safe to bundle |

## Sanitized feedback record

| User request or feedback | Response | Observable result | Remaining limit |
| --- | --- | --- | --- |
| Start a user story for a viewer refinement while keeping the experience View-Only and deferring editable dimensions. | Added explicit story, current scope, acceptance criteria, non-goals, and future direction sections. | The resulting document separates inspection from editing and labels future dimension entry and gesture ideas as deferred. | Device-specific VR interaction details remain implementation-time decisions. |
| Add the planning document to the applicable `.gitignore`. | Located the nested repository and added only the exact filename pattern to its `.gitignore`; did not commit or push. | `git check-ignore` confirmed the pattern matches. | The workspace root itself was not a Git repository, so the ignore rule was scoped to the discovered nested repository. |
