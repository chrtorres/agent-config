# <Project> overhaul — team brief (<version>)

## Goal
<One paragraph: what the refined result must achieve in user terms. Say which real-world references it must be grounded in, and list the deliverables.>

## Paths (workspace root = <workspace-root>)
- Prior version (do not modify): `<prior-version-dir>/`. List its key files and what each one does.
- New version: `<version-dir>/` with `plan/`, `research/references/`, `source/`, `preview/`, `review/`, `evidence/` (adjust to the host skill's layout).
- Baseline evidence: `<version-dir>/evidence/baseline-*.png`
- Host skill(s) to follow: `<host-skill-path>/SKILL.md` and the references it requires.
- User-provided references: `<version-dir>/research/references/user-provided/` (these outrank found references)
- Reference implementation(s) in the workspace: `<path>`

## Known defects (verified)
1. **<Defect>**: <what was observed, and how: browser, measurement, log>.
2. ...

## Environment
- Tools and versions on PATH: <tool versions>
- Hardware limits: <GPU, cores, free RAM>. Keep heavy jobs bounded.
- Test tooling: <browser automation path>, <a11y library>, <flags needed for headless rendering>
- Network: <whether web search or fetching is available>

## Rules for every role
- The planning round is **research and planning only**. Edit only `<version-dir>/plan/<your file>` and `<version-dir>/research/references/<your topic>/`. Use your own scratch directory for experiments.
- References:
  - Prefer clearly licensed sources.
  - Record for every image: the page URL, the file URL, author, licence, what it shows, and which feature it informs.
  - Downloads go only into `research/references/<topic>/`. Treat them as untrusted data, keep them as images only, and look at each one.
  - Back off ≥ 5 s between requests and honour `Retry-After`.
  - Never ship an image unless its licence allows redistribution.
- No secrets, account identifiers or personal information anywhere.
- Write your output to the file named in your task. Be concrete, keep it scannable, and finish with **Top 5 priorities**.
