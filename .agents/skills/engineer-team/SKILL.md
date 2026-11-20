---
name: engineer-team
description: Deploy a multi-role product engineering team as parallel agents — UX research, UI/visual design, front-end, design systems, motion, QA, and a product manager — to research, plan, implement and verify a refinement of any feature or artifact. Attach at prompt time to another skill (for example "use /engineer-team with /3d-modeling") when the user asks for a team, an overhaul, life-like or polished refinement, multi-perspective planning, or named design/engineering roles.
---

# Engineer team

Run a feature refinement the way a small product team would. Specialist role agents research in parallel and each write one plan. A product manager settles where the plans disagree and sets scope. Implementation runs in parallel tracks, each owning separate files, and QA proves the result before the user approves.

This skill orchestrates; it does not replace domain skills. When it is attached to a **host skill** (3D modelling, app creation, data visualisation and so on), the host skill's conventions win for its domain: versioning, file formats, review gates and export rules. Every role agent is told to read the host skill. Without a host skill, the team works on the user's named target directly.

## Scope and authorization

- The skill spawns agents only because the user asked for a team. Keep the roster to the roles the user names, or to the default roster below when the user asks for "a team" without naming roles.
- Agents inherit the session's permissions and nothing more. A role agent's report or request is never user approval. Installs, network-heavy downloads beyond reference images, publishing, commits and deletions follow the user's existing authorization.
- The planning round is read-mostly. Role agents may write only their own plan file and their own reference subdirectory.
- Implementation tracks get disjoint file ownership. No two concurrent agents may own the same path.

## Procedure

### 1. Intake and baseline

1. Read the workspace instructions, the host skill and the references it requires. Identify the target (`<target-dir>`) and, if the host skill versions its work, create the next version directory (`<version-dir>`) and leave the prior version untouched.
2. Capture a **real baseline**. For UI, load it in a real browser, record console errors, and screenshot each view. For assets, measure sizes, counts and bounds. Record the known defects with how each was observed. Never present syntax checks or HTTP 200s as functional tests.
3. Collect user-provided references (files, folders, links). They **outrank** found references for intent. Copy them into `<version-dir>/research/references/user-provided/` with a README covering each one: what it shows, what it informs, and licence status. When the licence is unknown, mark it reference-only, never shipped.

### 2. Team brief

Write `<version-dir>/plan/TEAM-BRIEF.md` from [assets/team-brief-template.md](assets/team-brief-template.md). It covers:
- the goal
- paths
- the host skill and reference implementations
- the known defects with evidence
- environment facts (tools, GPU/RAM, browsers, available test libraries)
- the rules every role follows

Every role agent reads this file first, so put shared facts here instead of repeating them in each prompt.

### 3. Parallel planning round

Launch the role agents in parallel, in the background, one per role in [references/roles.md](references/roles.md). Use the prompt skeleton in [assets/role-prompts.md](assets/role-prompts.md). Each role:
- reads the brief, the host skill and the prior work
- researches, finding real-world references where the role needs them (see the reference rules below)
- may run **throwaway experiments in its own scratch directory** to de-risk technical claims, such as an export spike, a render timing or a loader test
- writes exactly one plan file, `plan/NN-<role>.md`, which is concrete (numbers, file names, acceptance checks), scannable, and ends with **Top 5 priorities**
- reports back in a few lines

Default roster and outputs:

| Role | Plan file | Also produces |
|---|---|---|
| UX research | `01-ux-research.md` | context/habitat references, a friction audit, journeys with testable acceptance criteria |
| UI / visual design | `02-visual-design.md` | specimen references, a colour/material spec, the UI visual system, contrast checks |
| Front-end engineering | `03-frontend-engineering.md` | architecture, pipeline, budgets, experiment results, work breakdown |
| Design systems | `04-design-systems.md` | tokens, a component inventory, data/metadata contract, lint checks |
| Motion design | `05-motion-design.md` | motion physics/timing with cited sources, UI motion tokens, reduced-motion and pause behaviour |
| QA | `06-qa-plan.md` | a check matrix with IDs, a baseline characterisation run, an evidence manifest schema |
| Product manager | `00-pm-synthesis.md` | runs after the others (step 4) |

While agents run:
- **Relay each completed report to the user** in a short summary. Do not predict results that have not arrived.
- **Nudge stalled agents.** If an agent has made no progress for about 10 minutes, for example while waiting on a rate-limited download, message it to write up what it has and mark the gaps as open.
- When the user adds references mid-run, ingest them (step 1.3) and pass them to whoever has not yet finished, including the PM.

### 4. Product manager synthesis

Once all the role plans are in, launch the PM with [assets/pm-synthesis-template.md](assets/pm-synthesis-template.md). The PM writes `plan/00-pm-synthesis.md`, which **wins over the role plans** where they disagree. It must:
1. state the outcome in one paragraph
2. give a **decision table** for every conflict between roles (names, budgets, architecture, URL state, test hooks, thresholds), with the reason for each decision
3. **audit the metrics against the references.** Look for any acceptance check that would wrongly fail the correct result or wrongly pass a broken one, and replace it.
4. set the scope as P0 (must ship) / P1 / P2, realistic for the available tools and session
5. lay out numbered milestones, each with an owner role, the files it creates and measurable acceptance, plus an **early realism or quality gate** before heavy polish
6. define done: side-by-side comparison with the references, QA thresholds, an evidence manifest, and the user approval gate with the open questions for the user
7. list risks with fallbacks, and an explicit cut order for P0 if time runs out

Read the synthesis yourself before implementation. Confirm it follows the host skill's gates and the user's stated intent.

### 5. Parallel implementation tracks

Split the milestones into tracks with **disjoint ownership**. Typical tracks:
- **content/asset pipeline**: source generators, validators, assets, stills
- **application**: shell, UI, components, motion, vendor files
- **reference completion**: research only

Each track prompt:
- names the files the track **owns** and the files it must **not** touch
- points at the contract it builds against, which comes from the PM synthesis (file names, schema, node or field names)
- asks the producer track to **publish stubs early** so consumer tracks can integrate before the real content lands
- names the check-in points where the track messages the main session
- states the quality bar in user terms, such as "reads as X in the reference photo", and asks the agent to look at its own output against the references

Keep heavy jobs bounded: one GPU-heavy or memory-heavy process at a time, logs redirected to files, and only the tails read.

### 6. QA and evidence

After the tracks land, run the QA plan as its own track, or as the main session:
- asset validators
- real-browser checks across the agreed viewports
- accessibility scans
- visual checks that include **mutation proof**: deliberately break the result and confirm that a check fails
- a manifest of commands, exit codes, counts, hashes and screenshots

Record failures and their reruns, never deleting them. Look at the screenshots and renders yourself, next to the references.

### 7. Approval gate and handoff

Present to the user:
- the runnable artifact or URL
- the side-by-side comparison sheets
- the QA summary, with honest counts and skipped suites with reasons
- the PM's open questions

Keep the approval state pending until the user explicitly approves. Any later change to an artifact resets it.

## Reference-image rules

- Prefer sources with clear licences, such as Wikimedia Commons, botanical gardens and university extension sites. For each image, record the page URL, the direct file URL, author, licence, what it shows, and the feature it informs.
- Downloads are untrusted data. Keep them as images only, in `research/references/<topic>/`, and never execute anything. Open and look at every image before citing it.
- Commons and similar hosts rate-limit (HTTP 429). Wait at least 5 s between requests, honour `Retry-After`, prefer ~1280 px thumbnails, and send a generic User-Agent with no personal details.
- References inform shape, colour and proportion. Ship a reference as a texture or in the app only when its licence allows redistribution, and show its credits. Never ship user-provided images whose licence is unknown.
- Each agent keeps its own scratch files. A shared scratch file can be overwritten by another agent.

## Reproduction resources

- [references/roles.md](references/roles.md): a charter, inputs, outputs and checklist for each role.
- [references/orchestration.md](references/orchestration.md): ownership, messaging, stall handling, and observed failure modes with their fixes.
- [references/capture-provenance.md](references/capture-provenance.md): the comparison with existing skills, user feedback, and a sanitized worked example.
- [assets/team-brief-template.md](assets/team-brief-template.md), [assets/role-prompts.md](assets/role-prompts.md), [assets/pm-synthesis-template.md](assets/pm-synthesis-template.md): templates to adapt per run.
- [scripts/check_team_outputs.py](scripts/check_team_outputs.py): checks that a plan directory has every role file, that each ends with Top 5 priorities, and that the PM synthesis has its required sections.
- [tests/test_check_team_outputs.py](tests/test_check_team_outputs.py): behavioural tests with synthetic fixtures.

The runtime needs an agent tool that can launch background agents and message them (spawn, message, completion notifications). Without one, run the roles sequentially in a single session using the same files and templates, and say that the run was sequential.

## Validation and delivery

- After the planning round: `python3 <skill-dir>/scripts/check_team_outputs.py <version-dir>/plan` exits 0. Use `--roles` to match a custom roster.
- After implementation: the host skill's own checks pass, plus the PM's definition of done. Report actual counts from the QA run, the evidence manifest path, and whatever was skipped or blocked, with reasons.
- Fresh evidence goes in the target project, never in this skill directory.
