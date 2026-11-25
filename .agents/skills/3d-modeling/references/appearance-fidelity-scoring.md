# Measured appearance-fidelity scoring against a reference image

Use this when the request is a numeric visual-match bar ("as close as possible", "≥ 99 % match")
against a single reference image, and the match is about *surface appearance* — the layout of
materials or markings, colour, grain and edge structure — not only silhouette or measured
dimensions. [photo-based-refinement.md](photo-based-refinement.md) covers dimensional and
landmark fidelity and deliberately refuses a visual percentage; this reference adds the
appearance metrics and the honesty rules that make a visual bar meaningful.

## What makes this different from a silhouette or landmark check

A silhouette IoU and a set of landmark residuals can both be excellent while the surface still
looks wrong: the wood bands in the wrong place, the charcoal too warm, the grain running the
wrong way. Score the appearance directly, each metric labelled by what it can establish.

## Procedure

1. **Fix one frame and one scale.** Choose the reference image as the single source of truth and
   record the pixel→mm scale and the crop/ortho window. Every render is produced in that same
   orthographic frame at that scale so comparisons are pixel-aligned. Keep the window in a small
   JSON next to the scores.
2. **Trace the interior, not just the outline.** Trace the material/marking boundaries (seams
   between bands, strand edges, markings) as well as the silhouette, and rasterise them into a
   reference **class map**: one integer per pixel — background, each material class, and a
   *don't-care* class for seams, slot walls and anything whose exact pixels you do not intend to
   score. Rasterise the reference at an integer supersample (e.g. 4×) so sub-pixel boundaries do
   not quantise the score.
3. **Render a flat class layer.** Give the model a per-pixel class colour (a vertex-colour
   attribute such as `StrandClass`, one flat RGB per class) and render it with lighting and view
   transform off, in the matched frame. Classify each rendered pixel to the nearest class colour;
   near-black pixels are don't-care; transparent pixels are background. This is the layer that is
   scored, *not* the beauty render — lighting must not move the score.
4. **Score each role and keep the roles separate** (the table below). Report every metric with its
   role word. Drive the loop on the *fit* metrics to the bar, then confirm nothing regressed on the
   *check* metrics.
5. **Judge appearance by eye against the metrics, and say when the eye wins.** A texture change can
   improve a grain metric and still look wrong (a fine noise layer raised measured contrast but read
   as granite speckle, not wood — it was dropped although the number improved). Record such a
   decision and why; the metric is evidence, not the goal.
6. **State the bar honestly.** Fit metrics tuned on the same trace that placed the geometry are a
   *build-reproduction* check, not independent verification — say so wherever the number appears, in
   the metadata and in any UI. Overall visual fidelity stays **unverified** without an independent
   dimensioned or calibrated reference, exactly as in the photo-based workflow.

## Roles and metrics

| Metric | Role | What it measures | Tool |
| --- | --- | --- | --- |
| F1/F2/F3 silhouette | fit | soft-IoU of part/whole silhouette vs the reference coverage | project `silhouette`/`score` + reference coverage masks |
| F4 class / strand map | fit | per-class IoU + mean IoU + pixel accuracy of the flat class layer, don't-care excluded | [score_appearance.py](../scripts/score_appearance.py) `classmap_iou` |
| R1 registration | check | silhouette IoU after independent landmark registration | [register_exemplar_overlay.py](../scripts/register_exemplar_overlay.py) |
| A2 colour | check | median sRGB per class → CIELAB **CIEDE2000** per class | `score_appearance.py` `dE2000` |
| E1 edge | check | edge precision/recall/F within a pixel tolerance at matched gradient density | `score_appearance.py` `edge_f` (or Canny) |
| A3 grain | check | high-pass contrast and structure-tensor coherence per class, ratio ≈ 1 | `score_appearance.py` `grain` |
| A1 SSIM | information | luminance SSIM; lighting/material differ, so directional only | optional |
| C1/C2 | check | topology assertions (e.g. one crown tip, one continuous strand) | project assertions |

`fit` = optimised toward, not independent. `check` = not directly optimised; a regression here is
real. `information` = context only, never a gate. Keep the same words in the review app's copy.

`score_appearance.py` computes the appearance metrics from PNGs/NPYs alone and hardcodes nothing
about a subject: classes are a name→sRGB map in class-id order. `classmap_iou` and `dE2000` need
only numpy + Pillow; `edge_f` and `grain` run when SciPy is importable and are reported as skipped
otherwise. Silhouette IoU and registration already have dedicated skill tools; landmark/dimension
residuals stay in [photo-based-refinement.md](photo-based-refinement.md).

## Long or repeated score builds

Scoring re-renders the model, which can take minutes, and an interactive session may end or wipe a
scratch venv mid-build. Put heavy, repeatable builds in a **durable project venv** and run them as a
**detached user job** (e.g. a `systemd --user` transient unit, or `nohup`) that writes a log and a
completion marker, then read the marker — do not hold the session open on the render. Keep the venv
and job runner inside the project so a later session re-attaches to the same tools. This matches the
lifecycle rules in [versioned-concept-handoff.md](versioned-concept-handoff.md): the durable build is
project infrastructure; temporary preview services are still stopped at cleanup.

## Synthetic reproduction

From an isolated skill copy, numpy + Pillow (SciPy optional for edge/grain):

```sh
python3 "<skill-dir>/tests/fixtures/make_appearance_fixture.py" --out "<run-dir>/fix"
python3 "<skill-dir>/scripts/score_appearance.py" \
  --render-classmap "<run-dir>/fix/render_classmap.png" \
  --ref-classmap    "<run-dir>/fix/ref_classmap.png" \
  --classes '{"walnut":[214,140,70],"charA":[96,60,40],"charB":[80,100,140]}' \
  --render-color "<run-dir>/fix/render_color.png" --ref-color "<run-dir>/fix/ref_color.png"
python3 -m unittest discover -s "<skill-dir>/tests" -p 'test_score_appearance.py' -v
```

The fixture shifts one band boundary by 4 px and tints the walnut band, so the run yields a mean
class IoU ≈ 0.97 (walnut 1.0, the two shifted bands ≈ 0.95), a clearly larger CIEDE2000 on the
tinted walnut band than on the untouched blue-grey band, and edge/grain reported when SciPy is
present. The overall fidelity remains unverified — the fixture exercises the metrics, not a match.

## Capture record

Compared against the pre-update skills with the skill-capture rubric (factors: outcome, inputs,
procedure, resources, validation order).

| Candidate | Factors | Score | Decision |
| --- | --- | ---: | --- |
| `3d-modeling` / [photo-based-refinement](photo-based-refinement.md) | 1, .75, .75, .5, .75 | 75% | Extend. Versioned reconstruction, the review gate, silhouette/landmark fidelity and the "unverified without independent CAD" honesty were already here. Missing: the interior class-map IoU, per-class CIEDE2000, grain and edge metrics, the fit-vs-check role separation and the numeric-bar honesty. Added as this sibling reference + one generalized scorer, keeping `3d-modeling` the single go-to. |
| `3d-modeling` / [versioned-concept-handoff](versioned-concept-handoff.md) | 1, .75, .5, .5, .5 | 65% | Related, below threshold. It carries approved-subassembly identity and the acceptance-layer language but its visual layer is explicitly qualitative. Cross-linked, not merged. |
| `full-stack-app-creation` / [versioned-3d-review-app](../../full-stack-app-creation/references/versioned-3d-review-app.md) | .25, .5, .25, .5, .5 | ~40% | Out of scope. The review app (draft discovery, Pending rendering, the headless-Chrome/DevTools check) is already captured from this project and needs nothing. |

Historical feedback, paraphrased. The user set a ≥ 99 % match bar against one hero image, asked to
iterate autonomously to it, and to keep a running handoff so an idle cache lost nothing. The response
defined the bar as measurable role-labelled metrics, drove the fit metrics to it, kept colour/grain/
edge/registration as checks, judged grain by eye when a metric disagreed, and labelled the fit scores
as non-independent and overall fidelity as unverified. Remaining limits: the bar is measured on the
placing trace; the back and interior depth are inferred; lighting sheen is not reproduced.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Class-map IoU + CIEDE2000 + edge/grain scorer | Generalized as [score_appearance.py](../scripts/score_appearance.py) (name→sRGB classes, no subject hardcoded) |
| Synthetic fixture + behavioural test | Bundled: [make_appearance_fixture.py](../tests/fixtures/make_appearance_fixture.py), [test_score_appearance.py](../tests/test_score_appearance.py) |
| Silhouette IoU, registration, landmark residuals | Reuse existing skill tools (`score`/`silhouette`, [register_exemplar_overlay.py](../scripts/register_exemplar_overlay.py), [compare_landmarks.py](../scripts/compare_landmarks.py)) |
| Project trace JSONs, reference image, measured class rasters, real renders, scores | Stay with the originating project — task inputs and evidence, subject-specific |
| Durable venv, job-runner unit names, ports, logs, markers | Excluded; discover runtimes and choose task-local names at execution time |

Generalized categories: usernames, absolute paths, project and version names, the subject's class
names and palette, image/scale constants, service/venv identities and timestamps. numpy and Pillow
are required; SciPy (edge/grain) and a Blender + flat-class render pipeline are external prerequisites
for the full, non-synthetic workflow.
