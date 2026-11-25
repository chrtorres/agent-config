#!/usr/bin/python3
"""Generate a slow single-layer concentric 'tendril' adhesion patch at bed center.
The nozzle spirals inward in one small spot (no long back-and-forth sweeps), so it
is forgiving while you babystep the nozzle down (via printer_stream.py) to find the
squish that makes a first layer actually stick. Prime line is kept inboard so it
clears edge clips. Heaters are left ON at the end (lifted) so you can continue.

Prints G-code to stdout:  adhesion_patch.py > patch.gcode

Tune the constants for your machine: BED center, NOZZLE/BED temps, PRIME_X inboard
of any bed clips, SQUARE size. Defaults assume a 220x220 bed and PLA.
"""
import math, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cx", type=float, default=110.0)   # bed center X
    ap.add_argument("--cy", type=float, default=110.0)   # bed center Y
    ap.add_argument("--half", type=float, default=15.0)  # half-size of the square patch
    ap.add_argument("--lw", type=float, default=0.45)    # line width
    ap.add_argument("--lh", type=float, default=0.20)    # first-layer height
    ap.add_argument("--nozzle", type=int, default=200)
    ap.add_argument("--bed", type=int, default=60)
    ap.add_argument("--feed", type=int, default=600)     # print feed (mm/min); 600 = 10 mm/s
    ap.add_argument("--prime-x", type=float, default=30.0)  # inboard of edge clips
    args = ap.parse_args()

    CX, CY, HALF, LW, LH, FP = args.cx, args.cy, args.half, args.lw, args.lh, args.feed
    EPMM = (LH * LW) / (math.pi * (1.75 / 2) ** 2)       # E per mm of travel (1.75 mm filament)

    def seg(x0, y0, x1, y1):
        d = math.hypot(x1 - x0, y1 - y0)
        return f"G1 X{x1:.3f} Y{y1:.3f} E{d*EPMM:.5f} F{FP}"

    L = ["; concentric adhesion / squish-finder patch", "G90", "M83",
         f"M104 S{args.nozzle}", f"M140 S{args.bed}", f"M190 S{args.bed}", f"M109 S{args.nozzle}",
         "G28", "G1 Z2.0 F3000",
         f"G1 X{args.prime_x} Y30 Z0.3 F5000",
         f"G1 X{args.prime_x} Y160 Z0.3 E15 F1500",           # prime line, inboard, not to the back edge
         f"G1 X{args.prime_x+0.4} Y160 Z0.3 F5000",
         f"G1 X{args.prime_x+0.4} Y30 Z0.3 E15 F1500",
         "G1 Z2.0 F3000"]
    sx, sy = CX - HALF, CY - HALF
    L += [f"G1 X{sx:.3f} Y{sy:.3f} F3000", f"G1 Z{LH:.3f} F600", "G1 E0.5 F300"]
    r, px, py = HALF, sx, sy
    while r > 1.0:
        corners = [(CX - r, CY - r), (CX + r, CY - r), (CX + r, CY + r), (CX - r, CY + r), (CX - r, CY - r)]
        L.append(seg(px, py, corners[0][0], corners[0][1]))
        for i in range(len(corners) - 1):
            L.append(seg(*corners[i], *corners[i + 1]))
        px, py = corners[-1]
        r2 = r - LW
        if r2 > 1.0:
            L.append(seg(px, py, CX - r2, CY - r2))
            px, py = CX - r2, CY - r2
        r = r2
    L += ["G1 E-1.5 F2100", "G1 Z6 F600", f"G1 X{CX:.1f} Y{CY+40:.1f} F3000",
          "; heaters left ON -- continue, or send M104 S0 / M140 S0 to stop"]
    print("\n".join(L))


if __name__ == "__main__":
    main()
