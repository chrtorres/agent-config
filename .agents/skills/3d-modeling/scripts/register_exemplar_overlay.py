"""Overlay a model's orthographic side silhouette on a reference figure (breed or product standard, catalogue
drawing), registered by one height landmark and the ground line.

    python3 register_exemplar_overlay.py --figure fig.png --ground-v 400 --landmark-uv 190 97 \
        --silhouette side_alpha.png --silhouette-map map.json --model-landmark-xz 4.5 41.0 \
        --out overlay.png [--figure-faces left|right] [--figure-mask mask.png] [--label text]

The figure scale comes from the landmark's height above the ground (for an animal, the withers), so the
figure is compared at the model's own height; no shape fitting is done. map.json describes the silhouette
render: {"px_per_unit": float, "origin_px": [u0, v0], "forward": "left"|"right"} where origin_px is the pixel
of model x=0 at ground z=0, model x grows toward `forward` on screen, and z grows upward.
The model outline is drawn in red over the figure and its interior tinted. With --figure-mask (white = subject)
the script also prints the silhouette IoU. Landmarks are hand-picked pixels, so treat the result as a visual
check with roughly the pick error (state it); it is not a fitted score.
"""
import argparse, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def figure_to_model(fu, fv, ground_v, land_u, land_v, land_x, land_z, figure_faces):
    k = (ground_v - land_v) / land_z                     # figure px per model unit
    sgn = -1.0 if figure_faces == 'left' else 1.0        # forward on the figure is screen-left or screen-right
    X = land_x + sgn * (fu - land_u) / k
    Z = (ground_v - fv) / k
    return X, Z, k


def model_to_silhouette(X, Z, m):
    s = -1.0 if m['forward'] == 'left' else 1.0
    u = m['origin_px'][0] + s * X * m['px_per_unit']
    v = m['origin_px'][1] - Z * m['px_per_unit']
    return np.round(u).astype(int), np.round(v).astype(int)


def project_mask(fig_size, alpha, m, ground_v, land_u, land_v, land_x, land_z, figure_faces):
    W, H = fig_size
    fu, fv = np.meshgrid(np.arange(W), np.arange(H))
    X, Z, k = figure_to_model(fu, fv, ground_v, land_u, land_v, land_x, land_z, figure_faces)
    u, v = model_to_silhouette(X, Z, m)
    ok = (u >= 0) & (u < alpha.shape[1]) & (v >= 0) & (v < alpha.shape[0])
    M = np.zeros((H, W), bool); M[ok] = alpha[v[ok], u[ok]]
    return M, k


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--figure', required=True); ap.add_argument('--ground-v', type=float, required=True)
    ap.add_argument('--landmark-uv', type=float, nargs=2, required=True)
    ap.add_argument('--silhouette', required=True); ap.add_argument('--silhouette-map', required=True)
    ap.add_argument('--model-landmark-xz', type=float, nargs=2, required=True)
    ap.add_argument('--figure-faces', choices=('left', 'right'), default='left')
    ap.add_argument('--figure-mask'); ap.add_argument('--out', required=True); ap.add_argument('--label', default='')
    a = ap.parse_args(argv)
    F = Image.open(a.figure).convert('RGB')
    im = Image.open(a.silhouette)
    alpha = (np.array(im.convert('RGBA'))[..., 3] > 127) if im.mode in ('RGBA', 'LA') else (np.array(im.convert('L')) > 127)
    m = json.load(open(a.silhouette_map))
    M, k = project_mask(F.size, alpha, m, a.ground_v, *a.landmark_uv, *a.model_landmark_xz, a.figure_faces)
    edge = np.array(Image.fromarray((M * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)) > 0
    G = np.array(F).astype(float); G[M] = G[M] * 0.75 + np.array([255, 120, 120]) * 0.25; G[edge] = [220, 0, 0]
    O = Image.fromarray(G.astype(np.uint8)); d = ImageDraw.Draw(O)
    d.line([(0, a.ground_v), (F.width, a.ground_v)], fill=(0, 140, 255))
    lu, lv = a.landmark_uv; d.ellipse([lu - 4, lv - 4, lu + 4, lv + 4], outline=(0, 140, 255), width=2)
    if a.label:
        d.rectangle([0, 0, 8 + 7 * len(a.label), 16], fill=(255, 255, 255)); d.text((4, 3), a.label, fill=(0, 0, 0))
    O.save(a.out)
    res = dict(scale_px_per_unit=round(float(k), 4), model_pixels=int(M.sum()))
    if a.figure_mask:
        R = np.array(Image.open(a.figure_mask).convert('L').resize(F.size)) > 127
        res['silhouette_iou'] = round(float((M & R).sum() / max(1, (M | R).sum())), 4)
    print(json.dumps(res))
    return 0


if __name__ == '__main__':
    sys.exit(main())
