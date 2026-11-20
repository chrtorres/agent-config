# Role charters

Each role writes one plan file. The plan is concrete, giving numbers, file names and checks that can be verified. It is scannable, with headings, tables and lists. It ends with **Top 5 priorities**. In the planning round a role may edit only its own plan file, its own `research/references/<topic>/` directory, and its own scratch directory.

## UX designer / researcher → `01-ux-research.md`
**Owns:** usability, friction points, navigation, and the real-world context the artifact lives in.
- Audit the baseline in a real browser. Cover first-frame comprehension, how discoverable the controls are, state persistence across views, error and loading states, keyboard and touch access, and target sizes.
- Gather **context references**: habitat, environment, typical usage scenes. Extract measurable numbers from them, such as proportions, coverage, colour of lit and shaded regions, lighting conditions and haze.
- Propose the information architecture, including view names and global controls, and how each view relates to its URL.
- Write 3–5 **user journeys**, each with acceptance criteria that can be tested with browser automation.

## UI / visual designer → `02-visual-design.md`
**Owns:** aesthetics — typography, colour and contrast, iconography, spacing, materials — and alignment with the design system.
- Gather **specimen references**, meaning close-ups of the subject's parts. Sample colours from them (median of a patch) and give each as sRGB hex plus a linear value. Mark any value not yet sampled as *(provisional)*.
- Write a material spec covering albedo limits, texture resolutions, alpha and double-sided rules, and what survives the export format.
- Specify the UI visual system: tokens it uses or proposes, light and dark themes, focus treatment over the canvas, icon approach, and mockups at desktop and mobile widths.
- Check contrast numerically, both UI text and subject against background, for example blossom against sky.

## Front-end engineer → `03-frontend-engineering.md`
**Owns:** turning designs into responsive, accessible, performant code: architecture, the asset pipeline, rendering and cross-browser behaviour.
- **Run experiments** in scratch to de-risk claims: export and loader round-trips, instancing, custom attributes, naming quirks, render timings, available and missing tools. Report each result as verified or unverified.
- Propose the architecture (renderer and context count, view lifecycle, caching), budgets (bytes, draw calls, triangles, load time), determinism (seeded randomness), and the data contract.
- Give a work breakdown with a risk rating for each step.

## Design systems engineer → `04-design-systems.md`
**Owns:** consistency across the application and its sibling projects.
- Survey existing apps and templates in the workspace for reusable patterns and for drift.
- Define role-named tokens (colour, space, radius, type, motion) for light and dark themes. Use small override files rather than forked components.
- Build a component inventory with fixed DOM and ARIA, and a metadata or data contract with a JSON example and validator rules.
- Write lint and automated checks that a script can run.

## Motion designer → `05-motion-design.md`
**Owns:** micro-interactions, transitions, loading states, and subject motion.
- Base physical motion on cited measurements, such as frequencies, speeds and damping. Separate measured values from artistic ones, and flag folklore numbers.
- Choose an implementation that respects performance, for example shader-based motion over per-object CPU transforms.
- Define UI motion tokens; the loading → error → retry flow; camera and transition timings; and a motion setting (Full / Reduced / Paused) with an always-visible pause control.
- Write the checks QA can automate, for example that a paused frame stays stable and that reduced motion produces no tweens.

## QA engineer → `06-qa-plan.md`
**Owns:** proving the result across screen sizes, devices, assistive tech and regressions.
- **Characterise the baseline** with real checks, not syntax checks, and record pass/fail counts with screenshots.
- Write a check matrix with stable IDs: asset checks, browser checks, a viewport matrix, accessibility (axe plus keyboard and screen-reader semantics), visual diff with mutation proof, and performance.
- Pair any check that can pass on a broken result with a sanity check. For example, "framed" is paired with "camera above ground".
- Specify a read-only test hook behind a query flag and an evidence manifest schema. Record unavailable browsers and tools as skipped, with the reason.

## Product manager → `00-pm-synthesis.md`
**Owns:** scope, prioritisation, and alignment on the outcome. Runs after the other roles.
- Resolve every conflict in a decision table with a reason for each. User intent and user references outrank everything else.
- Audit the metrics against the references and replace any check that would fail the correct result.
- Set P0 / P1 / P2 scope realistic for the tooling and time. Write milestones with an owner, the files each creates, and its acceptance, plus an early quality gate. Write the definition of done, the approval gate with open questions for the user, and risks with fallbacks and a P0 cut order.

## Optional roles
Add one only when the user names it or the domain clearly needs it, and give it its own plan number from `07` upward. Examples: content or domain researcher, accessibility specialist, performance engineer, technical writer.
