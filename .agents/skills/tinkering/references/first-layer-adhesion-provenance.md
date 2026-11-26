# Provenance — first-layer adhesion and print-window verification

Capture record for the material added to this skill: [first-layer-adhesion-recipe.md](first-layer-adhesion-recipe.md),
`scripts/check_print_window.py`, `scripts/vendor_gcode_profile.py`, `tests/test_print_window_tools.py`.

## Source task

A multi-part enclosure frame had to be printed on a consumer FDM printer whose every print was failing.
The vendor's own SD-card demo printed perfectly on the same bed, which located the fault in the slicer
profile rather than the hardware; the profile was rebuilt from that demo and a coupon then printed clean
with a raft that separated in one piece. A later coupon's thin T-slot lip broke under hand pressure, which
separated "settings that make a print stick" from "settings that make a print strong".

## Extend-or-create comparison

Scored against this skill's contents **before** the update, per the shared comparison rubric.

| Candidate | Outcome 25 | Scope 15 | Procedure 35 | Resources 15 | Validation 10 | Score | Action |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `tinkering` (this skill) | 0.5 | 0.75 | 0.25 | 0.5 | 0.25 | **42.5 %** | extended on explicit user direction |
| `3d-modeling` | 0.25 | 0.25 | 0 | 0.25 | 0.25 | 16.25 % | rejected for the printer-side method; received the design-side method instead |
| `system-health-diagnostic` | 0 | 0 | 0 | 0 | 0.25 | 2.5 % | rejected — host diagnostics, not device output |

Evidence for the `tinkering` factors:

- *Outcome 0.5* — §6 already owns driving a Marlin-class printer and warns to keep moves clear of bed
  clips, so "get a usable print off this machine" is partly its journey; it did not cover diagnosing a
  failing first layer.
- *Scope 0.75* — the skill already triggers on "troubleshooting a USB-connected 3D printer", the same
  request that produced this work.
- *Procedure 0.25* — deriving a profile from a vendor demo, the negative-Z-offset trap, tearaway raft
  tuning, the raft footprint budget, and splitting adhesion settings from strength settings were all
  absent. `scripts/adhesion_patch.py` tackles adhesion from the opposite direction (a live squish finder)
  and does not subsume them.
- *Resources 0.5* — `printer_serial.py`, `printer_stream.py` and the serial reference support the domain
  but perform none of this method.
- *Validation 0.25* — the serial reference covers slicing and the SD workflow; nothing verified a sliced
  file against a safe window.

**42.5 % is below the 75 % threshold, so the rubric alone would route this to a new focused skill.** The
user directed that this skill and `3d-modeling` be updated instead. That explicit direction takes
precedence and is recorded here rather than being disguised by adjusting the score. The extension is scope
compatible: it adds no new authorization, touches no hardware by itself, and both helpers are read-only
file parsers. Existing callers and resources are unchanged.

## Feedback captured

| User request (paraphrased) | Change made | Observed outcome | Remaining limit |
| --- | --- | --- | --- |
| Reported the raft "pulled apart perfectly", with photos | Recorded 5-layer raft at 0.14–0.15 contact distance as the tearaway baseline | Confirmed by the printed coupon | Contact distance is material and nozzle dependent; stated as a range to tune |
| "The rail was a little weak — I squeezed the ends of the opening and one of the flat sides broke off… ok if the purpose is not a strong one" | Separated the proven adhesion settings from strength settings: first layer untouched, upper-layer temperature raised, running fan reduced | Applied to a re-sliced part set; **not yet printed** | Unverified in print — the strength change is reasoned, not measured |
| "Maybe it just needed more time, I don't know, but something to note" | Recorded the failure honestly as a thin-feature/bonding issue rather than asserting a single cause | — | Root cause not isolated between geometry and layer bonding |
| Supplied additional vendor G-code and said it was the last | Built `--diff` so several vendor files separate the machine profile from per-model settings | Run on three real vendor files: 18 settings identical, 1 differing | Only two slicer dialects are parsed |

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Window-extent parser (written ad hoc several times during the task) | Generalized into `scripts/check_print_window.py` with CLI window/margin parameters |
| Vendor profile reader and diff | Generalized into `scripts/vendor_gcode_profile.py`, both slicer dialects |
| Recipe values (temperatures, raft, speeds) | Documented in the reference as a worked example, labelled as one machine's derived values |
| Vendor G-code files (~66 MB, third-party) | **Not bundled.** They ship on the printer's own SD card; the procedure says how to read your own |
| The source project's build script and sliced output | Not bundled — project specific; the reusable method is the reference plus helpers |
| Printer serial/streaming helpers | Unchanged; already in this skill |
| Behavioural tests | `tests/test_print_window_tools.py`, fixtures generated at run time |

## Generalized values

Generalized to parameters or placeholders: filesystem paths, SD-card mount points and volume labels, the
project directory, and output file names. The printer make and model and its derived temperatures, raft
settings and safe window **are stated concretely**, because a recipe without its numbers is not a recipe —
the user asked specifically for a record of what works. They are framed as one verified example with the
method for deriving your own. No credentials, tokens, account identifiers, hostnames or usernames appear.

## Validation performed

Run from an isolated copy of the skill, outside the source project:

- `python3 -m unittest discover -s tests -p test_print_window_tools.py` — 15 tests, all passing.
- `check_print_window.py` over a real 20-file print pack: measured extents per file; correctly flagged
  files at a 2 mm safety margin that pass at 0 mm.
- `vendor_gcode_profile.py --diff` over three real vendor files: 18 shared settings, 1 differing
  (`generateSupport`), first extruding Z = 0.45 for all three.

The smoke run exposed a defect: the first-layer Z was read only from a line carrying both Z and E, so it
returned nothing for files that raise Z on its own line. Fixed to track the last commanded Z, with two
regression tests added. Results above are from after the fix.

Not established: that these settings transfer to another printer, that the strength changes survive a
printed load test, or that the raft tears away cleanly for materials other than PLA.
