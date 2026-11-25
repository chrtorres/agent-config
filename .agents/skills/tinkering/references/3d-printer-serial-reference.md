# 3D printer control over USB serial (8-bit Marlin / Creality-class)

Driving an FDM printer (Ender-3-class, Marlin on an 8-bit board, no probe) directly
over its USB serial port: inspect firmware, tune, list the SD card, and stream a
print with live squish control. Treat heating + motion as **state-changing** — get
authorization, keep the user in the loop, and never leave a hot printer unattended.

## Connect

- Port: `ls -l /dev/ttyUSB* /dev/ttyACM*`. CH340-based Creality boards appear as
  `/dev/ttyUSB0`. The user must be in the **`dialout`** group (`id`); otherwise the
  port is `root:dialout` and unreadable.
- Only ONE program owns the port at a time. If a GUI host (Pronterface/OctoPrint) is
  **connected**, your `pyserial` open fails (busy) — have the user Disconnect it, or
  drive through it. A GUI that is *open but not connected* leaves the port free.
- Baud: stock Creality Marlin = **115200** (some builds 250000). Garbled banner = wrong baud.
- Opening the port usually toggles DTR and **resets the board** (heaters off, motors
  released, re-home needed) — a clean known state. Wait ~3–4 s for the boot banner.

## Safety invariants (learned the hard way)

1. **Closing the serial port does NOT cool many 8-bit boards.** After ANY stop/abort,
   explicitly send `M104 S0` and `M140 S0` (and read `M105` to confirm targets are 0).
   Kill-signalled background streamers may skip their cleanup — verify temps dropped.
2. **Keep every move inside the bed, clear of bed clips.** A raft/print reaching the
   edge can knock a glass bed off its clips. Bound prime, print, and the end "present"
   move to a safe inner box (e.g. X30–180 / Y30–170 on a 220 bed). Verify by parsing
   the sliced G-code's min/max X/Y before sending.
3. **Never leave it printing unattended** (fire). The user watches the first layer.

## Useful G-code (read-only unless noted)

| Command | Purpose |
|---|---|
| `M115` | firmware name/caps. `AUTOLEVEL:0` + `Z_PROBE:0` = manual-level machine (no mesh/`M851`). |
| `M503` | dump saved EEPROM: steps `M92`, accel `M204`, jerk `M205`, PID `M301`/`M304`. |
| `M105` | read temps (`T:` hotend, `B:` bed). |
| `M114` | current position. |
| `M211` | soft-endstop state + travel limits. |
| `M303 E0 S<temp> C8 U1` | hotend PID autotune, 8 cycles, apply to RAM *(heats; no motion)*. `E-1` = bed. |
| `M301 P.. I.. D..` + `M500` | write PID to EEPROM. **Tune FIRST, then save** — saving before the tune stores stale values. |
| `M290 Z<delta>` | babystep Z live (needs BABYSTEPPING; probe with `M290 Z0` -> ok). Persists through `G28`; cleared by power cycle. **State-changing.** |
| `M21` / `M20` | mount / list SD card files (8.3 names). **No command returns a file's contents** — pull the card to read/compare it. |
| `M104/M109`, `M140/M190` | set / set-and-wait hotend & bed. |

## Manual-level machines: squish is physical, not software

No probe = no `M851` offset, no mesh. Z=0 is the endstop; first-layer gap is set by
the **bed knobs + Z-endstop bracket**. `M290` babystep only trims live and is not
persistent/deterministic across resets. **Do not chase adhesion by babystepping the
nozzle far down** — on a correct endstop that starves flow and clogs the nozzle, and
corners drag. If you need a big negative offset to stick, the endstop/knobs are wrong.

Guided manual level: heat bed, `G28`, then park the nozzle at each corner and center
(inside the clip-safe box) while the user does the paper-drag test and turns that
corner's knob. Describe direction by **feel** ("the way that makes the paper drag more
raises the bed toward the nozzle"), not CW/CCW — it varies by machine.

## When prints fail but a sample prints fine: copy the known-good recipe

The fastest root-cause is a **known-good G-code from the same printer** (e.g. the
vendor's bundled sample on the SD card). Pull the card, read the sample's settings
block (Simplify3D/Cura/Creality Print write the full profile as `;` comments), and
match its first-layer strategy. A common pattern on a scratched/unlevel bare bed: the
working sample uses **lower temps, a thick slow first layer, a raft, and NO Z offset**,
while the failing prints squished too hard and ran too hot. Match temps, first-layer
height/width/speed, retraction, and accel/jerk before inventing new fixes.

Low first-layer **acceleration + jerk** (`M204 P<low>` / `M205 X<low> Y<low>`, e.g.
200 / 4) stop the nozzle whipping around corners and dragging the fresh line. A
**brim** anchors sharp corners. These, not glue, often fix "straights stick, corners drag".

## Slice with PrusaSlicer CLI

Keep output basic for an 8-bit board (no arcs/thumbnails). Discover the slicer at run
time (`which prusa-slicer` / `~/.local/bin/prusa-slicer`).

```sh
prusa-slicer --export-gcode --load <profile>.ini --center <cx>,<cy> \
  --temperature 200 --first-layer-temperature 200 --first-layer-bed-temperature 45 \
  --raft-layers 5 --raft-contact-distance 0.15 --raft-expansion 3 \
  <model>.stl --output <out>.gcode
# then CHECK extents before sending:
python3 - <<'PY'
import re; xs=[];ys=[]
for ln in open("<out>.gcode"):
    if ln.startswith(("G0","G1")):
        a=re.search(r"X([-\d.]+)",ln); b=re.search(r"Y([-\d.]+)",ln)
        if a: xs.append(float(a.group(1)))
        if b: ys.append(float(b.group(1)))
print("X",min(xs),max(xs),"  Y",min(ys),max(ys))
PY
```

If the profile's start/end G-code primes at the far edge or "presents" at X0/Y-max,
rewrite those coordinates inboard (string-replace in the `.ini` or the sliced file).

## Run the print: SD card vs. USB stream

- **SD card (preferred):** copy the `.gcode` to the card root, `sync`, verify with
  `cmp`, then `udisksctl unmount`/`power-off`. The user prints from the printer's
  screen — no host tether for the whole job. Leave old/bad-settings files alone or
  move them into a clearly named folder; don't delete without asking.
- **USB stream:** `printer_stream.py --file part.gcode` in the background. Dial squish
  live by writing nudges to the babystep file (`echo "-0.04" > babystep.txt`). Abort
  with a kill, then confirm heaters off. Only for supervised prints.

## Scripts (this skill, `scripts/`)

- `printer_serial.py` — one-off G-code / inspection / PID-tune-then-save / SD list / cooldown.
- `printer_stream.py` — stream a file with live `M290` babystep injection; aborts cold.
- `adhesion_patch.py` — generate a slow concentric single-layer squish-finder patch.

All take `--port`/`--baud`; bed size, temps and the clip-safe prime X are parameters
or constants to set per machine. Require `pyserial` (`python3 -c "import serial"`).
