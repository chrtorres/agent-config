# Capture record: breed-standard anatomy with an individual's coat

## Source task (sanitized)

A versioned SDF model of a pet dog had been fitted to the owner's photos and phone footage. Over two further versions:

- The user asked (paraphrased) to get the features as close as possible to the breed using the most recognized public resource and keep only the coat and pattern specific to the dog, fitting the real dog later. Response: anatomy from the national kennel club standard, its illustrated extended standard (figures of correct and faulty dogs) and a published morphometric study; 31 clause checks measured on the mesh (15/31 for the previous version, 31/31 after); markings carried through a torso warp; marking agreement with footage held at 0.925.
- Feedback (quote): "I checked the ears and the poke out dramatically from the side of the head, Dog ears don't do that. research". Response: veterinary ear anatomy (the cartilage rolls into a tube at the base, attached over muscle and fat); the ear base was modelled as a sunk, rolled tube; a new check of base overhang past the head line went 0.195 (old) → 0.114 (first draft) → 0.057 (fix), against exemplars at 0.07 and 0.00.
- The user added five new photos and asked for the next version. Response: coat-only changes (blaze shape measured on a grid, grey frosting as white flecks, one cheek's black extended per three photos, denser foreleg ticking, sparse chest speckles, saddle edge swept against footage, eye colour restored). Footage marking agreement 0.925 → 0.932, reported as a fit score. Two pre-build impressions were corrected by measurement and reported to the user.
- During the work, raising the head clipped the ear tips and the new stance clipped the hind feet at the grid edge; a boundary guard was added.

These are historical results from one task, not current passes.

## Skill comparison (skill-add rubric: outcome, scope, procedure, resources, validation)

| Candidate | Scores | Total | Evidence |
| --- | --- | --- | --- |
| 3d-modeling (research-driven + photo-based refinement) | 1, .75, .75, .5, .75 | 77.5% | Versioning, ledger, pixel calibration, viewer and approval gates already covered; population-vs-individual split, clause checks, warp-carried markings, coat flecks, side rule and fit-score sweeps were missing |
| full-stack-app-creation (evidence-linked review) | .25, .25, .25, .25, .5 | 27.5% | Covers browser review of evidence, not modelling; receives only a reporting rule |
| smoke-test | .25, .25, .25, .25, .5 | 27.5% | Browser behaviour only |

At or above 75% (weights 25/15/35/15/10), and named by the user: extend 3d-modeling. full-stack-app-creation gets a short cross-link for scored review metadata, as the user also named it.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Clause-check method, exemplar picks, warp, fleck algorithm, boundary guard | Generalized into the reference and `scripts/sdf_coat_demo.py` (synthetic quadruped) |
| Exemplar overlay | Generalized as `scripts/register_exemplar_overlay.py` (explicit silhouette map, either facing) |
| Footage scoring loop | Generalized as `scripts/sweep_params.py` (any build+score command printing JSON) |
| Gridded photo crops | `scripts/photo_measure_grid.py` |
| Shared multipart harness | Fixed in place (`tests/check_multipart_viewer.py`): copies all viewer modules, requests a frame from the on-demand renderer, hides the callout overlay during canvas diffs. Verified 36/36 against the bundled fixture |
| Dog model source, standard PDFs and figures, owner's photos and footage, renders | Excluded: subject-specific, private or third-party copyrighted. Obtain standards from the governing body |
| Pet name, owner details, local paths, machine values | Generalized or omitted |
