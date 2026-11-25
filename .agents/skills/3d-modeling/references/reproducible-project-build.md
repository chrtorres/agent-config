# Reproducible project build — recreate a finished project on demand

A finished modeling project should rebuild to its approved result on one command, and that command's
success should be *checked*, not assumed. A shared skill retains the *method*; the project directory
retains the exact materials to recreate *that* project. This reference is the contract that ties the
two together so "recreate that project" is automated and self-verifying — without copying any
project's bespoke meshes, traces or reference images into the shared skill.

## What every completed project leaves behind

At the approval gate (step 8 of the main procedure), before cleanup, leave the project able to
regenerate itself:

1. **One headless entrypoint.** A single command that rebuilds the approved artifacts from the
   versioned source with no interactive step — a build script, or `blender -b --python build.py`.
   It writes a completion marker (exit status + duration) so success is detectable without parsing
   logs. Keep it in the approved version directory.
2. **Pinned, discoverable dependencies.** Record the interpreter and library versions the build
   needs (a project venv plus a captured `pip freeze`, and the external tools with versions:
   Blender, a browser, ImageMagick). Discover runtimes at use time; pin what the result depends on.
3. **A `reproduce.json` manifest at the project root** naming the entrypoint, the artifacts it must
   produce (with a minimum size), and the recorded result metrics with tolerances (the same
   role-labelled scores from [appearance-fidelity-scoring.md](appearance-fidelity-scoring.md) or any
   measured check). This is the machine-readable definition of "reproduced correctly".
4. **The expected result recorded as numbers, not prose.** Put the approved metric values and their
   bars in the manifest so a rebuild that drifts is caught, not waved through because it "ran".

Heavy rebuilds run as a durable detached job (see
[appearance-fidelity-scoring.md](appearance-fidelity-scoring.md#long-or-repeated-score-builds)); the
manifest's entrypoint can be that same runner.

## Verifying a reproduction

[verify_reproduction.py](../scripts/verify_reproduction.py) (standard library only) reads the manifest,
runs the entrypoint, then checks the artifacts and metrics:

```sh
# full automated replay: rebuild from source, then verify artifacts + scores
python3 "<skill-dir>/scripts/verify_reproduction.py" "<project-dir>"
# validate the manifest / confirm the current approved build without a rebuild
python3 "<skill-dir>/scripts/verify_reproduction.py" "<project-dir>" --dry-run
```

It exits non-zero and names the failing row when the entrypoint fails, an artifact is missing or
undersized, or a metric drifts past its bar. Run `--dry-run` when authoring the manifest and after a
viewer-only change; run the full replay to prove the project still builds and scores as approved,
for example before archiving, after a dependency change, or when picking the project up again later.

Keep the verifier's role honest: it proves the build *regenerates the recorded result*. It does not
re-establish that the result is correct — that is the original review gate and the measured checks.
A reproduction passing only means the approved artifacts and numbers came back.

## Worked example

The Homelab Tree project carries a root `reproduce.json` whose entrypoint is its durable build runner
(`version-019/run_build.sh repro` → headless Blender), with the approved GLB, checks, renders and the
F1/F3/F4 silhouette-and-strand scores (bar 0.99) plus the C1/C2 topology checks. A full replay rebuilt
it from source in ~160 s and returned the same artifacts and scores; `--dry-run` confirms the manifest
against the currently approved build in under a second.

## Capture record

Compared against the pre-update skills with the skill-capture rubric (outcome, inputs, procedure,
resources, validation order).

| Candidate | Factors | Score | Decision |
| --- | --- | ---: | --- |
| `3d-modeling` | 1, .75, .5, .25, .5 | 60% | Extend. Versioned source, the approval gate and handoff were here, but nothing made a finished project *rebuild on command and self-check the result*. Added this contract, a stdlib verifier and a manifest schema so the skill delivers repeatable automated results, which is why it stays the single go-to for recreating past projects. |
| `3d-modeling` / [versioned-concept-handoff](versioned-concept-handoff.md) | 1, .75, .5, .5, .5 | 65% | Related. It defines the handoff and cleanup lifecycle this plugs into (the entrypoint survives cleanup; temporary previews do not). Cross-linked. |
| `verify-repository` | .5, .5, .25, .25, .5 | ~40% | Different scope. It checks a repository's claims in isolation; this replays a modeling project to its approved artifacts and scores. |

Historical feedback, paraphrased. The user said that once a modeling project is complete they expect
the skill to recreate any of those projects again on demand, repeatably and automatically — the skill
must retain the experience, not just a write-up. The response made each finished project a one-command,
self-checking reproducible build and proved it by rebuilding a completed project from source to its
approved result, while keeping the bespoke project source in the project rather than in the shared skill.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Manifest-driven reproduction verifier | Generalized as [verify_reproduction.py](../scripts/verify_reproduction.py) (stdlib only, no subject hardcoded) |
| Synthetic project + behavioural test | Bundled: [test_verify_reproduction.py](../tests/test_verify_reproduction.py) |
| `reproduce.json` for a real project | Lives at that project's root — it names that project's versions, entrypoint, artifacts and scores |
| Project Blender source, venv, build logs, GLBs, renders | Stay with the project; they are the exact materials to recreate it, versioned there, not in the shared skill |

Generalized categories: usernames, absolute paths, project/version names, entrypoint commands, marker
and artifact paths, metric pointers and bars, venv/service identities and timestamps. Python 3 is the
only prerequisite for the verifier; a project's own entrypoint names its heavier tools (Blender, a
browser) and their versions in its manifest.
