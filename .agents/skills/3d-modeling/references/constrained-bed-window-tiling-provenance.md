# Provenance — constrained bed-window tiling

Capture record for [constrained-bed-window-tiling.md](constrained-bed-window-tiling.md),
`scripts/plan_window_tiles.py` and `tests/test_plan_window_tiles.py`.

## Source task

A 342 × 355 mm open frame had been split into four quadrants sized for a nominal 220 mm bed. The printer's
*proven* window turned out to be far smaller, so the assembly had to be re-split: tiles resized for the
joint rather than the cell, a continuous slot feature relocated out of the tiled parts because it could
not cross a half-lap, and long narrow bars placed on the diagonal. The result was verified by parsing
every sliced file's real toolpath extents before anything was printed.

## Extend-or-create comparison

Scored against this skill's contents **before** the update.

| Candidate | Outcome 25 | Scope 15 | Procedure 35 | Resources 15 | Validation 10 | Score | Action |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `3d-modeling` (this skill) | 0.75 | 0.75 | 0.25 | 0.5 | 0.75 | **53.75 %** | extended on explicit user direction |
| `tinkering` | 0.25 | 0.25 | 0 | 0.25 | 0.5 | 13.75 % | received the printer-side method instead |
| `product-refinement` | 0.25 | 0.25 | 0 | 0 | 0.25 | 12.5 % | rejected — generic refinement loop, no print-geometry method |

Evidence for the `3d-modeling` factors:

- *Outcome 0.75* — the skill already owns preparing approved geometry for print export, checks oversize
  parts against a print volume, and states that oversize parts must be segmented with joints. The
  incoming work is the missing "how" behind that existing instruction.
- *Scope 0.75* — same trigger and same inputs: an approved parametric model heading for a print export.
- *Procedure 0.25* — that a half-lap tile grows by lap/2 per interior seam, the uneven-grid solve, the
  checkerboard tongue rule and its flipped poses, the depth constraint that stops a slot crossing a lap,
  and 45° placement for bars were all absent. Existing guidance said *that* parts must be split, not how
  to size the split.
- *Resources 0.5* — `render_print_meshes.py`, `build_print_previews.py` and `check_interference.py`
  support print prep; no tool computed a split.
- *Validation 0.75* — the existing mesh and slicer checks are reused unchanged and were sufficient for
  the geometry; only the window check was missing, and that lives in the companion skill.

**53.75 % is below the 75 % threshold**, so the rubric alone would route this to a separate skill. The
user directed that this skill be updated. That direction takes precedence and is recorded rather than
hidden by adjusting the score. The extension is scope compatible: it adds a planning helper and a
reference under the existing print-preparation step, changes no existing procedure, and expands no
authorization — physical printing still requires separate approval.

## Cross-skill dependency

Section 6 of the reference points at `check_print_window.py` in the `tinkering` skill for verifying
sliced output. That is a **soft reference, not an import**: `plan_window_tiles.py` runs standalone on the
Python standard library, and the tiling reference is usable without the other skill installed. If only
this skill is present, verify sliced extents by whatever means is available; the plan itself is unaffected.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Grid/lap arithmetic worked out during the task | Generalized into `scripts/plan_window_tiles.py` (even and uneven layouts, minimum cell count, 45° bar check) |
| Diagonal placement rule for long bars | Folded into the same helper as `--bar` mode |
| Design rules (lap growth, tongue parity, slot-vs-lap depth, empty cells) | Written up in the reference as general rules with the reasoning |
| The source project's Blender build script | **Not bundled** — project specific. Its reusable decisions are the reference's sections 2–4 |
| Concrete part geometry, STLs, sliced G-code | Not bundled; they are one project's output, not reusable input |
| Behavioural tests | `tests/test_plan_window_tiles.py`, pure arithmetic, no external runtime |

## Generalized values

Generalized: project paths, part names, output locations. The numeric example (342 × 355 span, 20 mm lap,
117 × 130 window, 5.5 mm raft margin) is retained as a worked example and labelled as such, since the
arithmetic is unreadable without numbers. No machine identifiers, credentials, hostnames or usernames.

## Validation performed

From an isolated copy of the skill, outside the source project:

- `python3 -m unittest discover -s tests -p test_plan_window_tiles.py` — 15 tests, all passing, including
  a property check that the chosen cell count always satisfies the budget while one fewer does not.
- CLI run reproducing the source task's grid: 342 × 355, lap 20, window 117 × 130, raft 5.5 → a 4 × 4
  uneven grid with every tile 100.5 mm on X, matching the geometry actually built and sliced.
- `--bar 214x16` correctly reports that 45° placement is insufficient and a split is required.

Two test premises were wrong on first run and were corrected rather than the tool being changed to match:
the even-vs-uneven comparison needed a budget that actually separates the two layouts, and the width-sum
assertion needed a tolerance consistent with the reported rounding.

Not established: that a tiled assembly at these sizes is structurally adequate, or that any particular
joint survives service load. The helper sizes parts for a printer; it does not analyse the structure.
