# First-layer adhesion and clean-tearaway raft (FDM, Marlin/Creality-class)

How to get a print to stick on a worn bed, and how to make the raft come off in one piece afterwards.
Written from a verified result on a Creality Ender 3 (dual-Z mod, stock 220 bed, heavily scratched surface,
no glue), but the method generalizes: the point is *derive the recipe from a print the machine already
succeeds at*, rather than tuning from first principles.

## When to use

- Prints spaghetti, clump on the nozzle, or lift at the corners, and it is happening to **every** part
  including small ones. That is a first-layer problem, not a model problem. Do not redesign the part, and
  do not split it into smaller pieces — small parts fail on a bad first layer too, usually worse.
- A bed is scratched, unlevel, or of unknown condition and a long multi-part job is about to start.

Two helpers in this skill do the mechanical parts:

```sh
# read / compare the vendor demo profiles that shipped on the SD card
python3 scripts/vendor_gcode_profile.py <card>/*.gcode --diff

# check your own sliced files against the safe window before printing any of them
python3 scripts/check_print_window.py --window <xmin>,<xmax>,<ymin>,<ymax> gcode/*.gcode
```

## Method: steal the recipe from the vendor's own test print

Every consumer printer ships with a sliced demo model on its SD card that was tuned for that exact machine.
If the vendor model prints perfectly on the same bed where yours fails, the difference is in the *settings*,
not the hardware.

1. Print the vendor demo from the SD card, unmodified, on the same bed, with no glue.
2. If it succeeds, open its G-code and read out the first-layer block: nozzle and bed temperature,
   first-layer height, first-layer speed, raft/brim settings, and where on the bed it sits.
3. Rebuild your slicer profile around those numbers. Change nothing else until a coupon prints.
   `vendor_gcode_profile.py --diff` across several vendor files separates the machine profile (values
   identical in every file) from per-model choices (support, build time), so you only copy the former.
   It also reports the Z of the first extruding move, which is the true first-layer height - slicers
   often express it as a percentage of layer height, and the raft's base layer is thicker than both.
4. Print a small coupon of your own geometry with that profile before committing to long parts.

## The recipe this produced (verified: clean print, raft peeled off in one piece)

| Setting | Value | Why |
| --- | --- | --- |
| Nozzle, first layer | 200 °C | Vendor demo value; hotter was *not* better |
| Bed | 45 °C | Low bed temp; high bed temp was part of the original failure |
| First layer height | 0.4–0.45 mm | Thick first layer tolerates an unlevel/scratched bed |
| Z offset / babystep | **0** | See the trap below |
| First layer speed | ~9 mm/s | Slow enough to lay a wide, well-squashed bead |
| Raft | 5 layers, contact distance 0.15 mm, expansion 1.5 mm | Gives the tearaway base |
| Fan, first layers | off for layer 1 | Cooling the first layer is what lifts corners |
| Placement | small, centred, inboard of the bed clips | Edges of a worn bed are the worst region |

**The trap: do not chase adhesion with a negative Z offset.** A nozzle pushed almost onto the bed cannot
extrude. The filament has nowhere to go, flow stops, the hot end clogs, and the nozzle then drags through
whatever did stick. The symptom (nothing sticking) looks identical to "nozzle too high", so it is easy to
babystep in exactly the wrong direction. If prints fail with a negative offset dialled in, zero it first.

## Why a raft, and getting a clean tearaway

A 5-layer raft at 0.15 mm contact distance separates in one sheet, by hand, with no tools and no marks on
the part. It is worth the extra ~10–15 minutes per print because:

- The raft, not the part, is what has to stick to the damaged bed. Part geometry stops mattering.
- A part with small or thin footprints (bars, rails, pegs) gets a large, uniform footprint underneath it.
- Corner lift is absorbed by the raft.

Tune `raft_contact_distance` if it comes off wrong: too small and it fuses to the part, too large and the
first part layer droops. Around 0.15 mm is the usable middle.

**Budget the raft into the footprint.** The raft is wider than the part: with
`raft_expansion = 1.5` and `raft_first_layer_expansion = 1.5`, measure roughly **5–5.5 mm of raft on every
side**. On a bed with a restricted safe window this is the difference between a part fitting and the nozzle
dragging through a bed clip, so verify the sliced G-code's real extrusion extents rather than trusting the
model dimensions (see "verify, don't assume" below).

## Separating adhesion from strength

The proven recipe is an *adhesion* recipe, and its two weakest-for-strength settings — a cool nozzle and
full fan — only matter from layer 2 upwards. So keep the first layer exactly as proven and raise the rest:

- `first_layer_temperature` stays at the proven value; `temperature` goes up ~15 °C for better layer bonding.
- `disable_fan_first_layers = 1` stays; drop the running fan to ~70 % instead of 100 %.
- Give genuinely load-bearing parts more perimeters and infill rather than more material elsewhere.

This was prompted by a real failure: a printed T-slot rail at 200 °C/100 % fan snapped at the slot lip under
a hand squeeze. Thin features that something bolts against need both geometry *and* bonding attention.

## Verify, don't assume

After slicing, parse the G-code and check the real extrusion extents against the machine's safe window,
skipping the start-G-code prime lines (they usually sit at the window edge and will mask the measurement):

```sh
python3 scripts/check_print_window.py --window 30,147,30,160 --margin 2 gcode/*.gcode
```

It skips the start block by default (pass `--include-start` to audit the prime lines themselves for clip
collisions), ignores travel moves, carries the last commanded X/Y through moves that omit an axis, and
exits non-zero if anything lands outside. `--margin` adds required clearance, which is the honest way to
ask "would this still be safe if my window estimate is 2 mm optimistic?".

Compare against the clip-safe window, not the nominal bed size, and keep a couple of millimetres clear of
the prime line as well as the clips. Measure where the clips actually are rather than inferring the window
from the size of a part that happened to print.

## Order of operations when prints are failing

1. Zero any Z offset / babystep.
2. Square the gantry (on a dual-Z machine, equal motor-top-to-gantry gap on both lead screws), then level.
3. Print the vendor demo from SD. If that fails too, the fault is mechanical, not profile.
4. Rebuild the profile from the demo's first-layer block; add a raft.
5. Print a small coupon of your own geometry and confirm the raft tears away cleanly.
6. Only then start the long parts.
