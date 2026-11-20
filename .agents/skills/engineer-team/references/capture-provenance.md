# Capture provenance

## Source task (sanitized)
The user asked for a team of agents to plan an overhaul of a procedurally generated 3D cherry-blossom tree project (three varieties, a browser review app, runtime GLBs). The roles were UX research, UI/visual design, front-end, PM, design systems, motion and QA. The team was to find real-life reference images of the habitat and foliage and return life-like visuals. The user then asked for the method to be captured as a skill named `engineer-team` that could be attached at prompt time to any of their other skills.

## Existing-skill comparison (score is coverage of the incoming workflow)

| Candidate | Outcome 25 | Inputs 15 | Procedure 35 | Resources 15 | Validation 10 | Score | Decision |
|---|---|---|---|---|---|---|---|
| plan-session | 0.25: writes one planning doc, not a team | 0.25: a feature request | 0.25: user-story structure only; no roles, synthesis or implementation | 0: no resources | 0.25: a doc consistency check | 21.25 % | separate |
| full-stack-app-creation | 0.25: builds an app, but with one engineer | 0.25 | 0.25: covers implementation and browser testing, not multi-role orchestration | 0.25: app templates (reused by a host, not duplicated) | 0.5: real browser verification | 27.5 % | separate; attach as a host |
| 3d-modeling | 0.25: a 3D domain workflow | 0.25 | 0.25: research ledger and review gate, single agent | 0.25 | 0.5 | 27.5 % | separate; attach as a host |
| smoke-test | 0: verification only | 0.25 | 0.25: covers the QA phase only | 0.25 | 0.5 | 18.75 % | separate |

All candidates are below 75 %, so this is a **new focused skill**. Domain skills are referenced as hosts rather than copied.

## User feedback → response → observed outcome → limit
- *"Create a team of agents … UX, UI/Visual, Front-End, PM, Design Systems, Motion, QA."*
  - **Response:** a default roster with charters (`references/roles.md`); six parallel role agents plus the PM.
  - **Observed:** six plans and a PM synthesis were produced, and `check_team_outputs.py` passed 28/28 on the real plan directory.
  - **Limit:** implementation quality depends on the host skill and the tools available.
- *"Find REAL LIFE source images … capturing the habitat and the foliage."*
  - **Response:** the reference-image rules in SKILL.md, including licence ledgers, rate-limit backoff and look-before-cite; habitat references assigned to UX and specimen references to Visual.
  - **Observed:** 12 habitat and 3 specimen Commons images were gathered with ledgers.
  - **Limit:** HTTP 429 from Commons stopped specimen downloads, so a separate reference-completion track was added.
- *User mid-run: "refer to [a folder] for more images."*
  - **Response:** ingest the user's references into `user-provided/` with a README of uses and licence status, rank them above found references, and pass them to the PM.
  - **Observed:** the folder name differed slightly (singular vs plural) and was found by listing nearby. One duplicate was skipped.
  - **Limit:** web-sourced user images have unknown licences, so they are kept as reference-only.
- *Earlier in the same project:* a "hung loading" bug had been reported while the earlier "smoke tests" were only HTTP and syntax checks.
  - **Response:** step 1 requires a real browser baseline, and the QA role characterises the baseline.
  - **Observed:** the baseline run passed 18 of 36 checks and surfaced defects that the earlier checks missed.

## Resource disposition

| Item | Disposition |
|---|---|
| Team brief, role prompts, PM prompt | generalized into `assets/` templates |
| Role charters, orchestration lessons | `references/` |
| Planning-output checker plus tests | bundled `scripts/` and `tests/`, using synthetic fixtures |
| The project's actual plans, images and code | **excluded**: project-specific, and some images have unknown licences |
| Agent-spawning runtime | external prerequisite, with a documented sequential fallback |

**Generalized values:** workspace, project and version paths; tool paths; ports; hardware figures; reference hosts other than the generic licensing advice. No account identifiers, user names or secrets are included.
