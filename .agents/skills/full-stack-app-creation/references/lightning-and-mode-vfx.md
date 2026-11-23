# Electric weather effects and a main-game / tutorial start

Apply this when a playable browser 3D game needs dramatic lightning around the player and in the
sky, and when one mode should become the main game while another becomes an opt-in tutorial, with
a toggle both ways. Start from [playable 3D regression and delivery](playable-3d.md) and
[cinematic presentation](cinematic-presentation.md); this section adds the effect and mode-start
decisions those lack. The runnable subset is [the lightning VFX example](../assets/lightning-vfx/README.md).

## Wide effect crown around the character

- Size the player aura to read at gameplay distance. A follow camera shows a ~2 m figure as a few
  hundred pixels, so a ~1 m coil looks cramped and the drama is lost. Put the coils 3–4.5× the body
  radius out (the example defaults to 2.4/3.8 m) and counter-rotate layers for motion.
- Keep the aura geometry static and animate it in the vertex/fragment shaders from a time uniform,
  parented to the player node so it follows for free. Set `toneMapped: false` and push core colors
  above 1 so an existing bloom pass makes it glow; it still draws without bloom.
- Throw forked strikes from the aura to the ground on a ring a few metres out, on a short random
  interval while the state that earns them is active (hovering, charging, a special). Pool a fixed
  number of bolt meshes and rewrite their buffers per strike; never allocate meshes per strike.
- Give the big beat its own shape: on a burst/ascend event, fire every pooled fork at once plus a
  shockwave ring that expands from zero. See [the crown module](../assets/lightning-vfx/crown.js).

## Visible sky and ground strikes

- Draw real forked bolts, not just a light pulse and a screen tint. Generate a channel by midpoint
  displacement with recursive branches from a seeded RNG (testable), build it as a camera-facing
  additive ribbon, and reuse a small pool. Place strikes on an annulus around the player (e.g.
  15–70 m) so they surround the camera, with occasional cloud-to-cloud bolts overhead and clusters.
- Light and sound with distance. Aim a shadowless key light at the nearest strike and scale its
  intensity, the rain/scene flash, and any camera shake by proximity. A real bolt re-strikes its
  channel, so use a multi-stroke envelope (`boltEnvelope`) rather than a single decay.
- **Photosensitivity.** Clustered near strikes can each trigger a full-screen flash. Rate-limit the
  flash (one per ~0.34 s) or flash once per cluster so it cannot exceed ~3 flashes/second. Honor
  reduced motion by suppressing strikes and flashes entirely and freezing the aura in a dim pose.

## Making one mode the main game and another a tutorial

- Resolve the opening mode from a pure function (`resolveStartMode`) so it is unit-testable and so
  automation keeps its contracts: an explicit `?start=` wins; `navigator.webdriver` keeps the old
  default (the tutorial) so every existing browser suite written against it still passes; a player
  with no main-mode save opens the main mode; otherwise the saved campaign's active flag decides.
  Add one opt-in value (`?start=player`) so a test can exercise the real player rule.
- Give the toggle a path both ways and reuse the existing enter/leave logic rather than forking it.
  Bind leave to a HUD control, a key, and a spare controller button; guard it while a menu is open
  and debounce the same press that dismisses a title card. Keep the enter path (menu button, start).
- **Protect the other mode's save.** Entering the main game must not overwrite the tutorial's saved
  position. Before switching, stash where the player stood (its own storage key) and restore it on
  return; only fall back to a spawn point when nothing valid is stored. This bug is invisible until
  a returning player toggles back and finds themselves at the trailhead — see the testing note.
- Update the title, headers and transition copy so the main game is presented first, and keep the
  automated-default banner wording stable where suites assert on it.

## Testing and review notes

- A reload test that keeps `?start=main` in the URL proves nothing about resume-from-save — the URL
  decides. Reload (or re-navigate) with the neutral `?start=player` so the save alone chooses the
  mode, and assert the tutorial position survived the round trip. A test that exercises nothing is
  worse than no test: it hides the save-overwrite bug above.
- Capacity fixtures must overflow. A bolt-buffer test whose path fits under capacity asserts on an
  empty draw and passes for the wrong reason; size the fixture past capacity and assert the main
  channel is kept and indices stay inside the written vertices.
- When an independent reviewer returns should-fix items, apply them and re-run the affected checks
  before delivery; record each as request → change → observed outcome. In the originating run the
  reviewer caught the save-overwrite, the inert reload test and the no-op capacity test above.
- **Stopping preview servers:** do not run `pkill -f <pattern>` or `for p in $(pgrep -f <pattern>)`
  in a shell command whose own text contains that pattern — it matches and kills the calling shell
  (exit 144), silently aborting whatever ran after it, including a gate. List PIDs with a
  bracket-grep that cannot match itself (`ps -eo pid,args | grep -E "[v]ite preview --port 4318"`)
  and `kill` them in a separate call. Confirm the port is released with `ss -ltnp`.
- A suite timing out under memory pressure is not a regression until the same suite fails on a
  detached worktree of the last commit; see [playable-3d](playable-3d.md#outfit-cloth-and-close-inspection).
  In the originating run the mission autopilot failed identically on the unmodified baseline, so it
  was reported as pre-existing, not caused by the change.

## Capture decision and provenance

Factors use the skill capture rubric in order: outcome, inputs, procedure, resources, validation.

| Candidate | Factors | Score | Evidence and routing |
| --- | --- | ---: | --- |
| full-stack-app-creation | 1, 1, .5, .25, .75 | 68.75% | Cinematic presentation and the playable fixture already cover effects-at-distance, reduced motion, isolated builds and same-origin saves; the effect crown, forked-bolt generation and mode-start resolver are new. The user named this target, and this extends the existing playable/cinematic workflow, so the method and a bundled example were added here. |
| 3d-modeling | .25, .25, .25, .25, .5 | 27.5% | Not model authoring; no Blender geometry. The shared server-stop safety note was added to its browser-review cleanup because it also launches HTTP review servers. |
| smoke-test | .25, .5, .25, .25, .5 | 32.5% | Reuse its isolated-browser evidence approach; it has no gameplay effects, modes or saves. |

| Resource | Disposition |
| --- | --- |
| Forked-bolt generation, pooled bolt mesh, sky field, effect crown, start-mode resolver | Bundled and generalized as [the lightning VFX example](../assets/lightning-vfx/), with a three stub so tests run with no install. |
| Originating game (campaign, shaders, scenery, saves, build history) | Retained in its task repository. The example reproduces the reusable method independently. |
| Shader color grades, world dimensions, save keys, project/mode names | Generalized into constructor options and parameters; concrete values stayed with the game. |
| Fresh gate output, screenshots, device and renderer identities, branch and port numbers | Retained outside the skill in task evidence. |

Historical feedback, paraphrased. The user asked to make the secondary "storm" mode the main game
and the original valley a tutorial, keeping the toggle, and to widen the lightning so it looked less
cramped and more explosive and elegant. The crown was widened from ~1 m to 2.4–3.8 m with forked
ground strikes and a burst shockwave, and the sky gained visible forked bolts; an independent review
then caught a save-overwrite on mode entry, an inert reload test and a no-op capacity test, which
were fixed and re-verified. Physical controller acceptance (the mode-toggle button) and in-engine
visual judgement of the effects remained hands-on checks beyond the automated results.

Generalized values include project, repository, branch and mode names, save keys, world dimensions,
local paths, ports, device and renderer identities, and evidence locations.
