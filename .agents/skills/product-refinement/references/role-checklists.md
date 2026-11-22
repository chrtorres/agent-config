# Role checklists

Apply each lens directly to the artifact and the same decision record.

| Lens | Questions | Record |
|---|---|---|
| User research | Who needs to act and what slows them down? Which user references establish the target? | One journey, starting state and observable outcome. |
| Visual design | Which shapes, materials, layouts and light establish the intended look? What confirms them at viewing scale? | Credited source and first side-by-side comparison. |
| Engineering | What owns state? What does a consumer receive? How do retries, stale responses and partial failures behave? | Boundary contract, budget and one early end-to-end run. |
| Design system | Which controls repeat? How do keyboard, focus, contrast and responsive layouts work? | Shared controls and token decisions, with browser assertions. |
| Motion | Which geometry changes? Can the user pause, resume and reduce motion? | Timing and state limits plus observed changes across rendered frames. |
| QA | Could a broken scene still pass? Does recovery work using delivered bytes? | Observable checks, deliberate mutations and reproducible evidence. |
| Product | Which requirements conflict? What ships now and what needs approval? | Decision with rationale, milestone and explicit review gate. |

Visual checks should pair a measurement with the condition that makes it meaningful. For example, projected height can pass for an occluded model, so also measure rendered subject coverage and world-space camera orientation. A hue threshold can miss correctly pale materials, so use a rendered object mask for coverage. Measure color separately under declared lighting.

Bound resource-heavy runs and retain individual logs. If a reference is rate limited, respect the source's retry instruction and record what evidence is available. Keep user photos with unknown licenses in private research and local review evidence. Retain source URLs, authors, licenses and the supported feature for redistributable images.
