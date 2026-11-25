"""Measured appearance-fidelity scoring: render vs a single reference image.

Scores the *surface appearance* of a reconstruction against one reference photo, beyond
silhouette and landmark fidelity. The headline metric is a per-class IoU over a flat
class-ID map (material/strand layout), which silhouette IoU and dimensional landmark checks
do not capture. Colour (per-class CIEDE2000) runs on numpy + Pillow alone; edge structure and
grain run only when SciPy is importable and are skipped with a note otherwise.

All inputs are caller-supplied PNGs/NPYs in one matched orthographic frame at one scale; this
helper hardcodes nothing about any particular subject. Classes are given as a name->sRGB map.

    python3 score_appearance.py \
        --render-classmap render_flat.png --ref-classmap ref_classes.png \
        --classes '{"walnut":[214,140,70],"charA":[96,60,40],"charB":[80,100,140]}' \
        [--render-color render_lit.png --ref-color source.png] \
        [--erode 2] [--dontcare-maxchannel 0.25] [--edge-tol 2] [--out scores.json]

Roles, kept separate and reported as such (see appearance-fidelity-scoring.md):
  classmap_iou  fit     per-class IoU + mean IoU + pixel accuracy of the class layout
  dE2000        check   median colour difference per class (CIELAB, CIEDE2000)
  edge_f        check   edge precision/recall/F within --edge-tol px (needs SciPy)
  grain         check   high-pass contrast + structure-tensor coherence per class (needs SciPy)

Fit metrics measured on the same trace that placed the geometry are NOT independent
verification; treat them as a build-reproduction check, not proof of visual match.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

try:
    from scipy import ndimage as ndi
    HAVE_SCIPY = True
except Exception:                           # colour + classmap still work without it
    HAVE_SCIPY = False


def _srgb_to_linear(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_xyz(rgb):                     # sRGB primaries, D65
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    return rgb @ m.T


def _xyz_to_lab(xyz):
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    e, k = 216 / 24389, 24389 / 27
    f = np.where(xyz > e, np.cbrt(xyz), (k * xyz + 16) / 116)
    x, y, z = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116 * y - 16, 500 * (x - y), 200 * (y - z)], -1)


def srgb_to_lab(srgb):
    return _xyz_to_lab(_linear_to_xyz(_srgb_to_linear(srgb)))


def delta_e_2000(lab1, lab2):
    """CIEDE2000 between two Lab triples (array-friendly, returns scalar for single pairs)."""
    lab1, lab2 = np.atleast_2d(lab1).astype(np.float64), np.atleast_2d(lab2).astype(np.float64)
    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp))
    dhp = np.where((C1p * C2p) == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2)
    Lbarp = (L1 + L2) / 2
    Cbarp = (C1p + C2p) / 2
    hsum = h1p + h2p
    hbarp = np.where(np.abs(h1p - h2p) > 180, (hsum + 360) / 2, hsum / 2)
    hbarp = np.where((C1p * C2p) == 0, hsum, hbarp)
    T = (1 - 0.17 * np.cos(np.radians(hbarp - 30)) + 0.24 * np.cos(np.radians(2 * hbarp))
         + 0.32 * np.cos(np.radians(3 * hbarp + 6)) - 0.20 * np.cos(np.radians(4 * hbarp - 63)))
    dtheta = 30 * np.exp(-(((hbarp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25.0 ** 7))
    Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / np.sqrt(20 + (Lbarp - 50) ** 2)
    Sc = 1 + 0.045 * Cbarp
    Sh = 1 + 0.015 * Cbarp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    de = np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                 + Rt * (dCp / Sc) * (dHp / Sh))
    return float(de[0]) if de.size == 1 else de


def load_rgb(path, size=None):
    im = Image.open(path).convert('RGBA')
    if size and im.size != size:
        im = im.resize(size, Image.BOX)
    a = np.asarray(im, np.float32) / 255.0
    return a[..., :3], a[..., 3]


def load_classmap(path, palette, dontcare_maxchannel, size=None):
    """Return an integer class map: 0 background, 1..N palette order, N+1 don't-care.

    .npy is taken as an authored class map directly (0 bg, 1..N classes, N+1 don't-care).
    A PNG is classified to the nearest palette colour; near-black pixels (max channel below
    the threshold) are don't-care (seams, slot walls, caps), transparent pixels background.
    """
    n = len(palette)
    if path.endswith('.npy'):
        cls = np.load(path).astype(np.int16)
        return cls, None
    rgb, alpha = load_rgb(path, size)
    pal = np.array([p for _, p in palette], np.float32) / 255.0
    d = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    cls = (np.argmin(d, -1) + 1).astype(np.int16)
    cls[rgb.max(-1) < dontcare_maxchannel] = n + 1          # don't care
    cls[alpha < 0.5] = 0                                     # background
    return cls, alpha


def _erode(mask, it):
    if it <= 0:
        return mask
    if HAVE_SCIPY:
        return ndi.binary_erosion(mask, iterations=it)
    out = mask.copy()                                        # 4-neighbour fallback
    for _ in range(it):
        s = np.ones_like(out)
        s[1:] &= out[:-1]; s[:-1] &= out[1:]; s[:, 1:] &= out[:, :-1]; s[:, :-1] &= out[:, 1:]
        out &= s
    return out


def classmap_iou(ref, ren, palette):
    n = len(palette)
    dc = n + 1
    care = (ref >= 1) & (ref <= n) & (ren != dc)
    out = {'dont_care_share': round(float(((ref >= 1) & (ref <= n) & (ren == dc)).sum()
                                          / max(1, ((ref >= 1) & (ref <= n)).sum())), 4)}
    ious = []
    for i, (name, _) in enumerate(palette, 1):
        inter = ((ref == i) & (ren == i) & care).sum()
        uni = (((ref == i) | (ren == i)) & care).sum()
        iou = float(inter / max(1, uni))
        out['iou_' + name] = round(iou, 4)
        ious.append(iou)
    out['mean_iou'] = round(float(np.mean(ious)), 4)
    out['pixel_accuracy'] = round(float((ren[care] == ref[care]).mean()) if care.any() else 0.0, 4)
    return out


def per_class_de(ref_cls, ref_color, ren_color, palette, erode):
    out = {}
    des = []
    for i, (name, _) in enumerate(palette, 1):
        m = _erode(ref_cls == i, erode)
        if not m.any():
            out[name] = None
            continue
        s = np.median(ref_color[m], 0)
        r = np.median(ren_color[m], 0)
        de = round(delta_e_2000(srgb_to_lab(s[None]), srgb_to_lab(r[None])), 2)
        out[name] = dict(ref_srgb=[round(float(x), 3) for x in s],
                         render_srgb=[round(float(x), 3) for x in r], dE2000=de, px=int(m.sum()))
        des.append(de)
    out['mean_dE2000'] = round(float(np.mean(des)), 2) if des else None
    return out


def _lum(rgb):
    return rgb @ np.array([0.299, 0.587, 0.114], np.float32)


def edge_f(ref_color, ren_color, mask, tol):
    """Edge precision/recall/F within `tol` px, at matched gradient quantile density."""
    def edges(l):
        gx, gy = ndi.sobel(l, 1), ndi.sobel(l, 0)
        mag = np.hypot(gx, gy)
        thr = np.quantile(mag[mask], 0.90) if mask.any() else mag.max()
        return (mag >= thr) & mask
    es, er = edges(_lum(ref_color)), edges(_lum(ren_color))
    ds, dr = ndi.distance_transform_edt(~es), ndi.distance_transform_edt(~er)
    prec = float((ds[er] <= tol).mean()) if er.any() else 0.0
    rec = float((dr[es] <= tol).mean()) if es.any() else 0.0
    f = 2 * prec * rec / max(1e-9, prec + rec)
    return dict(precision=round(prec, 4), recall=round(rec, 4), f=round(f, 4), tol_px=tol)


def grain(ref_cls, ref_color, ren_color, palette, erode):
    def stats(rgb):
        l = _lum(rgb)
        hp = l - ndi.gaussian_filter(l, 2.5)
        gx, gy = ndi.sobel(hp, 1), ndi.sobel(hp, 0)
        jxx, jyy, jxy = (ndi.gaussian_filter(a, 3.0) for a in (gx * gx, gy * gy, gx * gy))
        coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-9)
        o = {}
        for i, (name, _) in enumerate(palette, 1):
            m = _erode(ref_cls == i, erode)
            if m.any():
                o[name] = dict(contrast=round(float(hp[m].std() / max(1e-4, np.median(l[m]))), 4),
                               coherence=round(float(np.median(coh[m])), 4))
        return o
    ref, ren = stats(ref_color), stats(ren_color)
    ratio = {n: dict(contrast=round(ren[n]['contrast'] / max(1e-6, ref[n]['contrast']), 3),
                     coherence=round(ren[n]['coherence'] / max(1e-6, ref[n]['coherence']), 3))
             for n in ren if n in ref}
    return dict(photo=ref, render=ren, ratio=ratio)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--render-classmap', required=True)
    ap.add_argument('--ref-classmap', required=True)
    ap.add_argument('--classes', required=True, help='JSON name->[r,g,b] 0-255, in class-id order')
    ap.add_argument('--render-color')
    ap.add_argument('--ref-color')
    ap.add_argument('--erode', type=int, default=2)
    ap.add_argument('--dontcare-maxchannel', type=float, default=0.25)
    ap.add_argument('--edge-tol', type=int, default=2)
    ap.add_argument('--out')
    args = ap.parse_args(argv)

    palette = list(json.loads(args.classes).items())
    ref_cls, _ = load_classmap(args.ref_classmap, palette, args.dontcare_maxchannel)
    size = (ref_cls.shape[1], ref_cls.shape[0])
    ren_cls, _ = load_classmap(args.render_classmap, palette, args.dontcare_maxchannel, size=size)

    res = dict(roles=dict(classmap_iou='fit (not independent if measured on the placing trace)',
                          dE2000='check', edge_f='check', grain='check'),
               classmap_iou=classmap_iou(ref_cls, ren_cls, palette))

    if args.render_color and args.ref_color:
        ref_color, _ = load_rgb(args.ref_color, size=size)
        ren_color, _ = load_rgb(args.render_color, size=size)
        res['dE2000'] = per_class_de(ref_cls, ref_color, ren_color, palette, args.erode)
        if HAVE_SCIPY:
            fg = (ref_cls >= 1) & (ref_cls <= len(palette))
            res['edge_f'] = edge_f(ref_color, ren_color, _erode(fg, 3), args.edge_tol)
            res['grain'] = grain(ref_cls, ref_color, ren_color, palette, max(3, args.erode))
        else:
            res['edge_f'] = res['grain'] = 'skipped (SciPy not importable)'
    if not HAVE_SCIPY:
        res.setdefault('note', 'SciPy absent: edge_f and grain unavailable; classmap_iou and dE2000 computed')

    text = json.dumps(res, indent=2)
    if args.out:
        open(args.out, 'w').write(text)
    print(text)
    return res


if __name__ == '__main__':
    main()
