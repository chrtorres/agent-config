"""Generate a synthetic appearance-scoring fixture: a reference and a render that differ in a
known way, so score_appearance.py yields predictable numbers with no project data.

Three vertical class bands (walnut / charA / charB) on a transparent background, plus a thin
dark seam between them (don't-care). The render shifts the middle band's boundary by a few
pixels (lowers IoU predictably) and tints walnut slightly warmer (a small, known dE2000).

    python3 make_appearance_fixture.py --out <dir>
"""
import argparse
import os

import numpy as np
from PIL import Image

PAL = dict(walnut=(214, 140, 70), charA=(96, 60, 40), charB=(80, 100, 140))
DARK = (20, 18, 16)                 # seam / don't-care
W, H = 120, 180
B0, B1 = 40, 80                     # band boundaries in the reference


def classmap(b1):
    img = np.zeros((H, W, 4), np.uint8)
    img[:, :B0] = (*PAL['walnut'], 255)
    img[:, B0:b1] = (*PAL['charA'], 255)
    img[:, b1:] = (*PAL['charB'], 255)
    img[:, B0 - 1:B0 + 1] = (*DARK, 255)        # seams -> don't-care
    img[:, b1 - 1:b1 + 1] = (*DARK, 255)
    img[:6] = img[-6:] = 0                        # a little background top/bottom
    return img


def color(b1, warm):
    c = classmap(b1).astype(np.float32)
    rgb = c[..., :3]
    rgb[:, :B0, 0] = np.clip(rgb[:, :B0, 0] + warm, 0, 255)   # tint walnut red channel
    rgb += np.random.default_rng(0).normal(0, 3, rgb.shape).astype(np.float32)  # faint grain
    c[..., :3] = np.clip(rgb, 0, 255)
    return c.astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray(classmap(B1)).save(os.path.join(a.out, 'ref_classmap.png'))
    Image.fromarray(classmap(B1 + 4)).save(os.path.join(a.out, 'render_classmap.png'))   # 4 px shift
    Image.fromarray(color(B1, 0)).save(os.path.join(a.out, 'ref_color.png'))
    Image.fromarray(color(B1 + 4, 14)).save(os.path.join(a.out, 'render_color.png'))
    print('wrote fixture to', a.out)


if __name__ == '__main__':
    main()
