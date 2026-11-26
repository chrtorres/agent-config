#!/usr/bin/env python3
"""Check sliced G-code against a printer's SAFE print window, not its nominal bed size.

Model dimensions do not tell you where the toolpath lands: a raft, brim or skirt extends past the part,
and start-G-code prime lines usually sit right at the edge of the usable area. This reads the real
extrusion moves out of each file and compares them with a window you supply.

Why the prime lines are skipped: a typical start block draws one or two priming lines along the very edge
of the bed, so including them pins the measured minimum to that edge and hides where the part actually is.
Everything before the first non-Custom ';TYPE:' comment is treated as start G-code. Pass --include-start
to measure every extrusion instead, which is what you want when checking the start block itself for
collisions with bed clips.

Usage:
    check_print_window.py --window 30,147,30,160 gcode/*.gcode
    check_print_window.py --window 30,147,30,160 --margin 2 --json out.json gcode/*.gcode
    check_print_window.py --include-start --window 5,215,5,215 gcode/start_test.gcode

Exit status is 1 if any file falls outside the window (or if none could be measured), else 0.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MOVE_RE = re.compile(r'^G[01](?=[ \t])')
X_RE = re.compile(r'[Xx](-?\d+(?:\.\d+)?)')
Y_RE = re.compile(r'[Yy](-?\d+(?:\.\d+)?)')
E_RE = re.compile(r'[Ee](-?\d+(?:\.\d+)?)')
TIME_RE = re.compile(r'^;\s*estimated printing time \(normal mode\)\s*=\s*(.+)$', re.I)
GRAM_RE = re.compile(r'^;\s*(?:total )?filament used \[g\]\s*=\s*([\d.]+)$', re.I)
S3D_TIME_RE = re.compile(r'^;\s*Build time:\s*(.+)$', re.I)
S3D_GRAM_RE = re.compile(r'^;\s*Plastic weight:\s*([\d.]+) g', re.I)


def measure(path: Path, include_start: bool = False) -> dict:
    """Return extrusion extents plus whatever time/weight the slicer recorded."""
    xs: list[float] = []
    ys: list[float] = []
    time = ''
    grams = 0.0
    started = include_start
    # Track the last commanded position so a move that omits X or Y still contributes correctly.
    last_x = last_y = None
    with path.open('r', errors='replace') as fh:
        for line in fh:
            if line.startswith(';'):
                if not started and line.startswith(';TYPE:') and 'Custom' not in line:
                    started = True
                m = TIME_RE.match(line) or S3D_TIME_RE.match(line)
                if m and not time:
                    time = m.group(1).strip()
                m = GRAM_RE.match(line) or S3D_GRAM_RE.match(line)
                if m:
                    grams = max(grams, float(m.group(1)))
                continue
            if not MOVE_RE.match(line):
                continue
            mx, my = X_RE.search(line), Y_RE.search(line)
            if mx:
                last_x = float(mx.group(1))
            if my:
                last_y = float(my.group(1))
            if not started:
                continue
            me = E_RE.search(line)
            # Only extruding moves deposit material; travel moves may legitimately cross the window.
            if not me or float(me.group(1)) <= 0:
                continue
            if last_x is not None:
                xs.append(last_x)
            if last_y is not None:
                ys.append(last_y)
    if not xs or not ys:
        return dict(file=path.name, measured=False, reason='no extruding moves found')
    return dict(file=path.name, measured=True,
                x=[round(min(xs), 2), round(max(xs), 2)], y=[round(min(ys), 2), round(max(ys), 2)],
                size=[round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)],
                time=time, grams=round(grams, 1))


def judge(row: dict, win: tuple[float, float, float, float], margin: float) -> dict:
    if not row.get('measured'):
        row['ok'] = False
        return row
    x0, x1, y0, y1 = win
    lo_x, hi_x = row['x']
    lo_y, hi_y = row['y']
    over = []
    if lo_x < x0 + margin:
        over.append(f'X min {lo_x} < {x0 + margin}')
    if hi_x > x1 - margin:
        over.append(f'X max {hi_x} > {x1 - margin}')
    if lo_y < y0 + margin:
        over.append(f'Y min {lo_y} < {y0 + margin}')
    if hi_y > y1 - margin:
        over.append(f'Y max {hi_y} > {y1 - margin}')
    row['ok'] = not over
    row['violations'] = over
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+', type=Path)
    ap.add_argument('--window', required=True,
                    help='safe window as xmin,xmax,ymin,ymax in mm (the area proven clear of bed clips)')
    ap.add_argument('--margin', type=float, default=0.0,
                    help='extra clearance required inside the window, mm (default 0)')
    ap.add_argument('--include-start', action='store_true',
                    help='also measure start-G-code extrusions such as prime lines')
    ap.add_argument('--json', type=Path, help='write the full report here')
    args = ap.parse_args(argv)

    try:
        win = tuple(float(v) for v in args.window.split(','))
        if len(win) != 4 or win[0] >= win[1] or win[2] >= win[3]:
            raise ValueError
    except ValueError:
        ap.error('--window must be xmin,xmax,ymin,ymax with min < max')

    rows = [judge(measure(p, args.include_start), win, args.margin) for p in args.files]
    width = max((len(r['file']) for r in rows), default=4)
    for r in rows:
        if not r.get('measured'):
            print(f"{r['file']:<{width}}  -- {r['reason']}")
            continue
        flag = 'OK ' if r['ok'] else 'OUT'
        print(f"{r['file']:<{width}}  X{r['x'][0]:8.2f}-{r['x'][1]:<8.2f} Y{r['y'][0]:8.2f}-{r['y'][1]:<8.2f}"
              f"  {flag}  {r['time']:>12}  {r['grams']:6.1f} g")
        for v in r['violations']:
            print(f"{'':<{width}}    ! {v}")

    bad = [r['file'] for r in rows if not r['ok']]
    print(f"\n{len(rows)} file(s), window X{win[0]}-{win[1]} Y{win[2]}-{win[3]} margin {args.margin} mm")
    print('outside window: ' + (', '.join(bad) if bad else 'none'))
    if args.json:
        args.json.write_text(json.dumps(dict(window=list(win), margin=args.margin, files=rows), indent=1))
        print(f'report: {args.json}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
