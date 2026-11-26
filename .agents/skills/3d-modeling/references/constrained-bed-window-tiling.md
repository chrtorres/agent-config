# Designing a large printed assembly for a small, verified print window

Use this when a model is larger than what the printer can reliably produce — not larger than the nominal
bed, but larger than the **window that has actually been proven to print**, which on a worn or clip-loaded
bed is often much smaller. The job is to re-split an existing design into pieces that all fit that window
and still assemble into the same object.

## 1. Establish the window from a real print, not from the spec sheet

Take the extrusion extents of a print that succeeded and treat that as the budget. Subtract the raft
margin, which is bigger than people expect (~5–5.5 mm per side for a typical 1.5 mm raft expansion), and
keep a couple of millimetres clear of the start-G-code prime line as well as any bed clips. A 220 mm bed
can easily end up with a usable part footprint near 100 × 115 mm.

Record it as one number pair and design against it. Then verify every sliced file against it
programmatically — model dimensions do not tell you where the raft lands.

`scripts/plan_window_tiles.py` does the arithmetic in sections 2 and 5:

```sh
python3 scripts/plan_window_tiles.py --size 342x355 --lap 20 --window 117x130 --raft-margin 5.5
python3 scripts/plan_window_tiles.py --bar 214x16 --window 117x130 --raft-margin 5.5
```

It reports the even and uneven layouts side by side, the fewest cells each needs, and for a bar whether
45 deg placement is enough or how many pieces are required.

## 2. Tile the design, and size the tiles for the joint, not the cell

With bolted half-lap joints, a tile grows by half the lap length at **every interior seam it touches**:

```
tile extent along an axis = cell pitch + (lap / 2) x (number of interior seams on that axis)
```

An interior tile touches two seams per axis and an edge tile one, so a uniform grid produces tiles of two
different sizes and the interior ones are the constraint. Two fixes, usually combined:

- **Shorten the lap.** Going from a 30 mm to a 20 mm lap removes 10 mm from every interior tile. Keep two
  bolts per seam; place them at ±lap/4 and check the bolt-head counterbore still leaves ~2 mm of wall to
  the end of the tongue.
- **Make the grid uneven.** Give the edge columns more width and the interior columns less, so that
  `edge_width + lap/2 == interior_width + lap` and every tile comes out the same size. Solving that gives
  `interior = (span - lap) / n`, `edge = interior + lap/2`, uniform extent `interior + lap`, and a minimum
  `n = ceil((span - lap) / (budget - lap))`. This is usually what makes a borderline design fit.

Skip empty cells. An open perimeter frame will have grid cells that no member crosses; emit nothing for
them rather than an empty mesh.

## 3. Alternate the tongues, and accept that half the tiles print upside down

Checkerboard the lap parity — `tongue = 'bottom' if (ix + iy) % 2 == 0 else 'top'` — so every pair of
adjacent tiles mates bottom-to-top. A tile with top tongues must be exported flipped, because a top tongue
printed as-built is an unsupported ledge. Record the pose in the build report and in the print README; it
is the single easiest thing to get wrong at the printer.

Parity cannot be chosen per axis. Trying to give a tile bottom tongues on one axis and top tongues on the
other produces a part that is unprintable in either orientation.

## 4. What a half-lap cannot carry: continuous features

**A feature deeper than half the stock cannot cross a half-lap seam.** A T-slot profile needing 7 mm of
depth cannot run through a lap in 12 mm stock, because the lap is only 6 mm. Breaking the grid into more
rows therefore multiplies the dead zones in any continuous slot, channel, or wire run — and the dead zone
is wider than the lap itself: lap + the slicer-shy inset at each end + the length of whatever slides in it.

When that happens, **lift the continuous feature out of the tiled part**: make it a separate bar that bolts
on top of the tiles and butt-joints end to end. A butt joint leaves the slot continuous, the joint's
strength comes from both bars being bolted down to the structure underneath, and the bar — being narrow —
can be printed much longer than a tile (see §5). The cost is assembly height and hardware count, which is
almost always the better trade.

Fix narrow bars down through **ear pads** that widen the bar locally at the bolt positions, and widen the
member underneath to match, so the bolt lands on material. Choose the pad positions so that every copy of
the bar is the same part: position `p` in a repeated bar of length `L` lands at `k*L + p` globally, so pick
`p` values where no `k*L + p` falls inside a lap zone. One identical bar printed six times beats six
bespoke ones.

## 5. Long narrow parts go on the diagonal

A bar of length `l` and width `w` rotated 45° occupies a square of side `(l + w)/√2`. In a 117 mm window
that allows a bar of roughly 150 mm — around 50 % longer than printing it square-on. Slice with
`--rotate 45` and check the extents; it often turns a three-piece split into a two-piece one.

## 6. Build-report checks worth automating

Emit these from the build script every run, and fail loudly rather than discovering it at the printer.
Model dimensions are not enough - after slicing, verify the real toolpath with the companion helper in the
tinkering skill (`scripts/check_print_window.py`), because the raft is what actually hits the clips:

- footprint of each part against the window (and against the 45° square for rotated parts)
- non-manifold edge count per part (should be 0)
- which parts print flipped
- total bolt count by length, so the hardware list is derived rather than remembered
- the resulting stack height of the assembly, since lifting features out of tiles changes it

## 7. Count the cost before committing

Re-tiling multiplies print count. Quote the honest total — parts, prints, grams, hours — back to the user
before they start, and order the print list so a **small subset proves the joint first**: one block of
adjacent tiles that can be bolted together and checked for fit, ahead of the remaining dozen.
