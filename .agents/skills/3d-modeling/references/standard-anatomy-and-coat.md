# Breed-standard anatomy with an individual's coat

Use this workflow when a model of a specific animal (or another individual of a well-documented class) should first get **class-correct form from the most recognized public standard**, while only a named set of features, such as coat colour and markings, stays specific to the individual. The individual fit comes later as its own version. The same split works for a product family (catalogue drawing for the form, one unit's wear and decals for the surface).

It builds on [research-driven refinement](research-driven-refinement.md) (source ledger, fail-able checks) and [photo-based refinement](photo-based-refinement.md) (calibrated pixel picks). Keep the normal version, review and print-approval gates.

## 1. Split the evidence

Write the rule for the version at the top of the ledger, for example "anatomy from the standard; only coat colour and pattern are the individual's". Classify every source as **population** (the governing standard, its illustrated companion, published morphometric studies, veterinary or engineering anatomy) or **individual** (photos and footage of the subject). A feature belongs to exactly one class in this version. When the rule forces a visible departure from the individual (for example, eye colour the standard asks for), record it as a deliberate, revertible feature change.

Prefer the governing body's official text (for dog breeds, the national kennel club standard) and its illustrated or extended companion, which usually has the only figures of "correct" and "faulty" examples. Use published studies for numbers the standard gives only in words.

## 2. Turn clauses into fail-able checks

For each clause, write a check measured **on the final mesh**, with clause text, target, measured value and the interpretation it relies on:

- Words with numbers (a tail no longer than a quarter of a stated span) become direct checks.
- Population means from studies (for example craniofacial ratio, cephalic index) become a band around the mean.
- Words without numbers ("square", "in line with the elbows", "set wide") are measured on two or more of the standard's own **correct** exemplar figures with [photo_measure_grid.py](../scripts/photo_measure_grid.py), as ratios to a span in the same plane. Tolerances cover the spread between exemplars plus pick error (about ±5% on halftone prints). Store the picks in a landmark file.

Locate landmarks robustly: limit each search to the region it belongs to, because a raised neck, flared ears or a lowered head can capture a naive maximum. Run the checks on the previous version too, so the report shows which clauses the revision fixed.

Register a side render on a standard figure by height, not by fitting: [register_exemplar_overlay.py](../scripts/register_exemplar_overlay.py) pins one height landmark (for an animal, the withers at the top of the shoulder blade) and the ground line, then draws the model outline over the figure. It is a visual check; report it as such.

## 3. Reshape the form without losing the individual's markings

Change proportions through a **coordinate warp** applied to the body primitives, and evaluate the marking fields **through the same warp**, so every patch keeps its anatomical place. Move dependent parts (limb joints, tail) with the warp's forward map. Re-check joint angles afterwards; a warp can straighten a joint into a listed fault. Fill any dips it opens (for example a sag behind the shoulders) with a primitive rather than accepting a fault.

Report the individual-fit scores (silhouette, marking agreement against footage) as **information**: silhouette is expected to fall when the form follows the class; marking agreement staying high is the evidence the coat carried over.

## 4. Feedback on anatomy: research before editing

When the user reports a form that "real animals don't have" (in the captured run: ears that stuck out from the side of the head), look up the structure's anatomy (veterinary or engineering references), describe the real attachment or shape, model that mechanism, and add a check that measures the reported fault so it cannot return silently. Report the metric for the old version, the first draft and the fix, plus the exemplar values.

## 5. Refine the individual's coat from new photos

1. **Identify the side** before reading any marking: a subject facing image-right shows its **right** side (its right = forward × up points at the camera). In a front view, image-left is the subject's right. Write the side next to each photo in the ledger.
2. **Measure, don't eyeball.** Read widths on a gridded crop and express them as ratios to a same-plane span (head width at the eyes). Check the photo against a known model ratio (for example eye separation) to confirm the frame is usable. In the captured run, a first visual impression of the blaze shape was the reverse of the measurement.
3. **Weigh pose.** Crouches, sitting and turned heads stretch skin and move edges; prefer a natural stance for an edge's angle, and use stretched poses only to confirm presence and side.
4. **Resolve conflicts explicitly.** Where a low-resolution footage score and several clear photos disagree on a small region, follow the photos, report the score change, and say why.
5. **Score what can be scored.** Sweep marking parameters against the scored reference with [sweep_params.py](../scripts/sweep_params.py). It labels the winner a *fit* score; keep a holdout view if an improvement claim matters.
6. **Represent mixed-colour hair in a two-colour print** as flecks: dark ticking on white, and white "frosting" flecks inside black for grey hairs. State the printed fleck size at the chosen scale and whether the process can hold it.

## 6. Printable colour solids

Cut every colour solid from one body field with shared priority functions so the solids tile the body and each is closed. Build flecks in a thin skin, with the fleck radius measured tangentially to the surface so each fleck reaches the skin and none is an enclosed island; drop only sub-voxel slivers. Refuse to write a solid that touches the evaluation grid's edge: raising a head or widening a stance can push geometry out of the grid and cut it open silently (in the captured run, ear tips and hind feet were clipped until a guard was added). [sdf_coat_demo.py](../scripts/sdf_coat_demo.py) demonstrates all of this on an invented quadruped.

## Runnable synthetic reproduction

Python 3 with numpy, scipy, scikit-image and Pillow:

```sh
python3 <skill-dir>/scripts/sdf_coat_demo.py --out <run-dir>/demo                 # report.json: 0 boundary edges, tiling error < 1%
python3 <skill-dir>/scripts/sdf_coat_demo.py --out <run-dir>/clip --hi 16 9 15    # must exit 3: boundary guard
python3 -m unittest <skill-dir>/tests/test_standard_and_coat_tools.py -v
```

The tests check that the solids are closed and tile, that flecks exist in both colours, that the saddle edge follows the warp's forward map, that overlay registration recovers a known scale and mirroring, and that the sweep ranks a known optimum and labels it a fit score. Capture details are in [standard-anatomy-and-coat-provenance.md](standard-anatomy-and-coat-provenance.md).
