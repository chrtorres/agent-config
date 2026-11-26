#!/usr/bin/env python3
"""Plan how to split a large part into bolted half-lap tiles that each fit a printer's safe window.

The sizing trap this exists to avoid: with a half-lap joint a tile grows by lap/2 at EVERY interior seam
it touches, so an interior tile is lap/2 wider than an edge tile on each axis. Sizing the grid from the
cell pitch alone silently produces interior tiles that do not fit.

Two layouts are reported per axis:

  even    every cell the same pitch; the interior tiles are the constraint and the edge tiles waste window
  uneven  edge cells widened by lap/2 so that EVERY tile comes out the same size - usually the layout
          that makes a borderline design fit without adding another row or column

For the uneven layout, solving  2*(wi + lap/2) + (n-2)*wi = span  gives  wi = (span - lap)/n  and a
uniform tile extent of  wi + lap, so the minimum workable n is  ceil((span - lap) / (budget - lap)).

The budget is the window minus the raft, which is wider than the part. Measure your own slicer's raft
margin from a sliced file rather than trusting the nominal expansion setting; ~5-5.5 mm per side is
typical for a 1.5-3 mm raft expansion with a 0.4 nozzle.

Usage:
    plan_window_tiles.py --size 342x355 --lap 20 --window 117x130 --raft-margin 5.5
    plan_window_tiles.py --size 342x355 --lap 20 --window 117x130 --raft-margin 5.5 --json plan.json
    plan_window_tiles.py --bar 214x16 --window 117x130 --raft-margin 5.5    # long narrow part instead
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def even_layout(span: float, n: int, lap: float) -> dict:
    pitch = span / n
    extents = [pitch + lap / 2 * (1 if i in (0, n - 1) else 2) for i in range(n)]
    if n == 1:
        extents = [span]
    return dict(kind='even', n=n, widths=[round(pitch, 6)] * n,
                tile_extents=[round(e, 6) for e in extents], max_extent=round(max(extents), 6))


def uneven_layout(span: float, n: int, lap: float) -> dict | None:
    """Edge cells widened by lap/2 so every tile ends up the same extent."""
    if n == 1:
        return dict(kind='uneven', n=1, widths=[round(span, 6)],
                    tile_extents=[round(span, 6)], max_extent=round(span, 6))
    wi = (span - lap) / n
    if wi <= 0:
        return None
    we = wi + lap / 2
    widths = [we] + [wi] * (n - 2) + [we]
    extent = wi + lap
    # Rounded to 6 dp for readability; the widths then sum to the span to well under a micron, which is
    # far below any printable tolerance. Recompute from (span - lap) / n if you need exact rationals.
    return dict(kind='uneven', n=n, widths=[round(w, 6) for w in widths],
                tile_extents=[round(extent, 6)] * n, max_extent=round(extent, 6))


def min_n(span: float, lap: float, budget: float) -> int | None:
    """Fewest uniform tiles whose extent fits the budget, or None if the joint itself is too big."""
    if span <= budget:
        return 1
    if budget <= lap:
        return None
    return max(2, math.ceil((span - lap) / (budget - lap) - 1e-9))


def plan_axis(name: str, span: float, lap: float, budget: float) -> dict:
    n = min_n(span, lap, budget)
    if n is None:
        return dict(axis=name, span=span, budget=round(budget, 3), feasible=False,
                    reason=f'lap {lap} mm is not smaller than the {budget:.2f} mm budget')
    uneven = uneven_layout(span, n, lap)
    even = even_layout(span, n, lap)
    even_n = n
    while even['max_extent'] > budget and even_n < n + 4:
        even_n += 1
        even = even_layout(span, even_n, lap)
    return dict(axis=name, span=span, budget=round(budget, 3), feasible=True,
                uneven=uneven, even=even,
                even_needs_extra=even['n'] - uneven['n'])


def diagonal_side(length: float, width: float) -> float:
    """Square side a length x width bar occupies when placed at 45 degrees."""
    return (length + width) / math.sqrt(2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--size', help='overall part size as WxL in mm, e.g. 342x355')
    ap.add_argument('--bar', help='instead of a grid, test one long narrow part as LENGTHxWIDTH mm')
    ap.add_argument('--lap', type=float, default=20.0, help='half-lap length at each interior seam, mm')
    ap.add_argument('--window', required=True, help='safe print window as WxH in mm (clip-safe area)')
    ap.add_argument('--raft-margin', type=float, default=5.5,
                    help='raft/brim overhang beyond the part on EACH side, mm (measure it; default 5.5)')
    ap.add_argument('--json', type=str, help='write the plan here')
    args = ap.parse_args(argv)

    try:
        win_w, win_h = (float(v) for v in args.window.lower().split('x'))
    except ValueError:
        ap.error('--window must be WxH, e.g. 117x130')
    budget_w = win_w - 2 * args.raft_margin
    budget_h = win_h - 2 * args.raft_margin
    out: dict = dict(window=[win_w, win_h], raft_margin=args.raft_margin,
                     budget=[round(budget_w, 3), round(budget_h, 3)], lap=args.lap)
    print(f'window {win_w} x {win_h} mm, raft {args.raft_margin} mm/side '
          f'-> part budget {budget_w:.2f} x {budget_h:.2f} mm\n')

    if args.bar:
        try:
            length, width = (float(v) for v in args.bar.lower().split('x'))
        except ValueError:
            ap.error('--bar must be LENGTHxWIDTH, e.g. 214x16')
        side = diagonal_side(length, width)
        square_ok = length <= budget_w and width <= budget_h
        diag_ok = side <= min(budget_w, budget_h)
        pieces = 1 if diag_ok else max(2, math.ceil((length - args.lap) / (
            math.sqrt(2) * min(budget_w, budget_h) - width - args.lap)))
        out['bar'] = dict(length=length, width=width, square_fits=square_ok,
                          diagonal_side=round(side, 2), diagonal_fits=diag_ok, pieces_at_45=pieces)
        print(f'bar {length} x {width} mm')
        print(f'  square on the bed : {"fits" if square_ok else "does NOT fit"}')
        print(f'  rotated 45 deg    : occupies {side:.2f} mm square -> '
              f'{"fits" if diag_ok else "does NOT fit"}')
        if not diag_ok:
            print(f'  split into {pieces} pieces joined by a {args.lap} mm half-lap, printed at 45 deg')
        if args.json:
            open(args.json, 'w').write(json.dumps(out, indent=1))
            print(f'\nplan: {args.json}')
        return 0 if diag_ok or pieces > 1 else 1

    if not args.size:
        ap.error('pass --size WxL (a tiled part) or --bar LENGTHxWIDTH (a single long bar)')
    try:
        span_w, span_h = (float(v) for v in args.size.lower().split('x'))
    except ValueError:
        ap.error('--size must be WxL, e.g. 342x355')

    axes = [plan_axis('X', span_w, args.lap, budget_w), plan_axis('Y', span_h, args.lap, budget_h)]
    out['axes'] = axes
    for a in axes:
        print(f"axis {a['axis']}: span {a['span']} mm, budget {a['budget']} mm")
        if not a['feasible']:
            print(f"  INFEASIBLE - {a['reason']}\n")
            continue
        u, e = a['uneven'], a['even']
        print(f"  uneven  {u['n']} cells, widths {u['widths']} -> every tile {u['max_extent']} mm")
        print(f"  even    {e['n']} cells, pitch {e['widths'][0]} -> largest tile {e['max_extent']} mm"
              + (f"  (needs {a['even_needs_extra']} more cell(s))" if a['even_needs_extra'] else ''))
        print()
    if all(a['feasible'] for a in axes):
        nx, ny = axes[0]['uneven']['n'], axes[1]['uneven']['n']
        out['grid'] = [nx, ny]
        out['max_tile'] = [axes[0]['uneven']['max_extent'], axes[1]['uneven']['max_extent']]
        print(f'recommended: {nx} x {ny} uneven grid = {nx * ny} tiles '
              f'(minus any cell no member crosses), largest '
              f"{axes[0]['uneven']['max_extent']} x {axes[1]['uneven']['max_extent']} mm")
        print('checkerboard the tongues: bottom if (ix+iy) is even, else top (those tiles print flipped)')
    if args.json:
        open(args.json, 'w').write(json.dumps(out, indent=1))
        print(f'plan: {args.json}')
    return 0 if all(a['feasible'] for a in axes) else 1


if __name__ == '__main__':
    sys.exit(main())
