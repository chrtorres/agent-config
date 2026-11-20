# PM synthesis prompt and output skeleton

## Prompt

```
You are the Product Manager for <subject> <version>. Read <version-dir>/plan/TEAM-BRIEF.md, all role plans
(<version-dir>/plan/01…06*.md), and <version-dir>/research/references/user-provided/README.md. The user references outrank
everything else for intent; look at them. Write <version-dir>/plan/00-pm-synthesis.md (≤ 400 lines) and edit nothing else.
Context: <key experiment results and blockers reported by the roles>.
Constraints for scope: <who implements, tools, hardware, time>.
When done, report back in ≤ 10 lines.
```

## Required sections (checked by `scripts/check_team_outputs.py`)

```markdown
# 00 — PM synthesis
## 1. Outcome
<one paragraph>
## 2. Decisions
| # | Topic | Positions | **Decision** | Why |
## 3. Scope
### P0 …   ### P1 …   ### P2 …
## 4. Implementation sequence
| M | Milestone | Owner | Creates | Acceptance (measurable) |
## 5. Definition of done
<side-by-side vs references, QA thresholds, evidence manifest, user approval gate + open questions>
## 6. Risks
| # | Risk | Likelihood / impact | Fallback |
## Top 5 priorities
```

## Review checklist for the main session
- [ ] Every disagreement named in the role reports has a decision row.
- [ ] No acceptance metric fails the reference-correct result. Check colour and coverage metrics in particular.
- [ ] P0 fits the stated constraints, and there is a P0 cut order.
- [ ] An early quality gate comes before heavy polish.
- [ ] The approval gate matches the host skill's approval rules.
