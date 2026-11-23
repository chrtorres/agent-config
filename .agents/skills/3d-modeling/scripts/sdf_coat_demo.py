"""Synthetic demo: printable colour-region solids for a coat pattern on an implicit (SDF) body.

    python3 sdf_coat_demo.py --out <dir> [--voxel 0.2] [--warp-k 0.85]

Shows the method used for a patterned animal model, on an invented quadruped (no real specimen):
  * one body field; every colour solid is cut from it with shared priority functions, so the solids tile the
    body (sum of colour volumes == whole volume, to voxel precision) and each is closed;
  * a coordinate warp reshapes the torso (here: shortened behind a pivot), and the marking fields are evaluated
    through the SAME warp, so a patch keeps its anatomical place when the anatomy changes;
  * surface flecks (ticking / frosting): cellular-noise flecks in a thin skin, with the radius measured
    tangentially to the surface so every fleck reaches the skin and none is buried as an enclosed island;
    black flecks on white legs, white "frost" flecks inside a black head patch;
  * a guard that refuses to write a solid that touches the grid boundary (it would be cut open).
Writes whole/white/black.ply and report.json (faces, volumes, components, boundary edges, tiling error).
Requires numpy, scipy and scikit-image.
"""
import argparse, json, os, sys
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes


def ell(X, Y, Z, c, r):
    px, py, pz = (X - c[0]) / r[0], (Y - c[1]) / r[1], (Z - c[2]) / r[2]
    k0 = np.sqrt(px * px + py * py + pz * pz); k1 = np.sqrt((px / r[0]) ** 2 + (py / r[1]) ** 2 + (pz / r[2]) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def capsule(X, Y, Z, a, b, r):
    a = np.asarray(a, float); b = np.asarray(b, float); ba = b - a
    t = np.clip(((X - a[0]) * ba[0] + (Y - a[1]) * ba[1] + (Z - a[2]) * ba[2]) / (ba @ ba), 0, 1)
    return np.sqrt((X - a[0] - t * ba[0]) ** 2 + (Y - a[1] - t * ba[1]) ** 2 + (Z - a[2] - t * ba[2]) ** 2) - r


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)


class Warp:
    """new-world -> old (authoring) space: x behind `pivot` is stretched back by 1/k (the body got shorter)."""
    def __init__(self, pivot, k):
        self.p, self.k = pivot, k
    def apply(self, X):
        return np.where(X < self.p, self.p + (X - self.p) / self.k, X)
    def fwd(self, x):
        return self.p + (x - self.p) * self.k if x < self.p else x


def worley_centres(P, cell, seed):
    """Nearest jittered feature point (per 3-D cell) for points P (n,3): returns centre (n,3) and a [0,1) id."""
    g = P / cell; base = np.floor(g).astype(np.int64)
    best = np.full(len(P), 9e9); C = np.zeros_like(P); H = np.zeros(len(P))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + [dx, dy, dz]
                h = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791) ^ (seed * 2654435761)
                rng = (h.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)) >> np.uint64(11)
                j = np.stack([(rng >> np.uint64(s)) & np.uint64(1023) for s in (0, 10, 20)], 1).astype(float) / 1023
                hid = ((rng >> np.uint64(30)) & np.uint64(1023)).astype(float) / 1024
                pc = (c + j) * cell; d = np.linalg.norm(pc - P, axis=1); m = d < best
                best[m] = d[m]; C[m] = pc[m]; H[m] = hid[m]
    return C, H


def flecks(inside, idx, P, cell, seed, r, keep, depth):
    """Fleck field at near-surface voxels idx (tuple of arrays) with world points P; > 0 inside a fleck."""
    C, H = worley_centres(P, cell, seed)
    rad = r[0] + (r[1] - r[0]) * ((H * 7.31) % 1.0)
    nrm = np.zeros_like(P)
    for ax in range(3):                                   # outward normal from the depth field's gradient
        hi = list(idx); lo = list(idx)
        hi[ax] = np.minimum(idx[ax] + 1, inside.shape[ax] - 1); lo[ax] = np.maximum(idx[ax] - 1, 0)
        nrm[:, ax] = inside[tuple(lo)] - inside[tuple(hi)]
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    dv = C - P; dt = np.linalg.norm(dv - (dv * nrm).sum(1, keepdims=True) * nrm, axis=1)   # tangential distance
    val = np.where(H < keep, rad - dt, -1.0)
    return np.minimum(val, depth - inside[idx])


def build(voxel=0.2, warp_k=0.85, lo=(-22, -9, -1), hi=(16, 9, 26)):
    W = Warp(pivot=2.0, k=warp_k)
    ax = [np.arange(lo[i], hi[i] + voxel / 2, voxel) for i in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing='ij')
    Xo = W.apply(X)                                                     # torso authored in the old space
    F = ell(Xo, Y, Z, [-6, 0, 13], [11, 5, 5]) * 0.9
    F = smin(F, ell(X, Y, Z, [7.5, 0, 17], [3.6, 3.4, 3.4]), 2.0)       # head and neck (in front of the pivot: not warped)
    for fx in (4.0, W.fwd(-14.0)):                                      # legs move with the warped body
        for s in (-1, 1):
            F = smin(F, capsule(X, Y, Z, [fx, s * 3, 12], [fx, s * 3, 1.0], 1.2), 1.0)
    F = np.maximum(F, -Z)                                               # flat soles
    F = gaussian_filter(np.clip(F, -3, 3), 0.6).astype(np.float32)
    inside = -F

    saddle = np.minimum(-2.0 - Xo, Z - 9.5)                             # black behind x_old=-2, above the belly
    head_patch = 2.2 - np.sqrt((X - 7.5) ** 2 + (np.abs(Y) - 2.0) ** 2 + (Z - 18) ** 2)   # a black eye patch each side
    near = np.nonzero((inside > -0.3) & (inside < 0.9))
    P = np.stack([X[near], Y[near], Z[near]], 1)
    tick = np.full(inside.shape, -5.0, np.float32); frost = tick.copy()
    sel = P[:, 2] < 9.0                                                 # lower legs: black ticking
    v = flecks(inside, tuple(a[sel] for a in near), P[sel], 1.6, 11, (0.35, 0.5), 0.35, 0.6)
    tick[tuple(a[sel] for a in near)] = v
    sel = head_patch[near] > 0                                          # inside the black patch: white frosting
    v = flecks(inside, tuple(a[sel] for a in near), P[sel], 1.1, 5, (0.3, 0.42), 0.6, 0.6)
    frost[tuple(a[sel] for a in near)] = v

    black = np.maximum.reduce([saddle, np.minimum(head_patch, -frost), tick])
    white = -black
    out = dict(whole=inside, white=np.minimum(inside, white), black=np.minimum(inside, black))
    return out, ax, voxel


def mesh(field, ax, voxel):
    f = field.copy(); f[np.abs(f) < 1e-4] = -1e-4
    V, Fc, _, _ = marching_cubes(f, 0.0, spacing=(voxel,) * 3)
    V = V + [ax[0][0], ax[1][0], ax[2][0]]
    tri = V[Fc]; vol = np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if vol < 0:
        Fc = Fc[:, ::-1]; vol = -vol
    return V, Fc, float(vol)


def stats(V, Fc):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.sort(np.concatenate([Fc[:, [0, 1]], Fc[:, [1, 2]], Fc[:, [2, 0]]]), 1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    _, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(V), len(V))), directed=False)
    comp = len(np.unique(lab[np.unique(Fc)]))
    return dict(boundary_edges=int((cnt == 1).sum()), nonmanifold_edges=int((cnt > 2).sum()), components=comp)


def write_ply(path, V, Fc):
    with open(path, 'wb') as f:
        f.write(f'ply\nformat binary_little_endian 1.0\nelement vertex {len(V)}\nproperty float x\nproperty float y\n'
                f'property float z\nelement face {len(Fc)}\nproperty list uchar int vertex_indices\nend_header\n'.encode())
        f.write(V.astype('<f4').tobytes())
        rec = np.empty(len(Fc), dtype=[('n', 'u1'), ('i', '<i4', (3,))]); rec['n'] = 3; rec['i'] = Fc; f.write(rec.tobytes())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True); ap.add_argument('--voxel', type=float, default=0.2)
    ap.add_argument('--warp-k', type=float, default=0.85)
    ap.add_argument('--lo', type=float, nargs=3, default=(-22, -9, -1)); ap.add_argument('--hi', type=float, nargs=3, default=(16, 9, 26))
    a = ap.parse_args(argv)
    fields, ax, v = build(a.voxel, a.warp_k, a.lo, a.hi)
    os.makedirs(a.out, exist_ok=True); rep = {}
    lo = np.array([x[0] for x in ax]); hi = np.array([x[-1] for x in ax])
    for name, fld in fields.items():
        V, Fc, vol = mesh(fld, ax, v)
        if (V.min(0) < lo + 1.5 * v).any() or (V.max(0) > hi - 1.5 * v).any():
            print(f'ERROR {name}: mesh reaches the grid boundary; enlarge --lo/--hi', file=sys.stderr); return 3
        write_ply(os.path.join(a.out, f'{name}.ply'), V, Fc)
        rep[name] = dict(faces=int(len(Fc)), volume=round(vol, 3), **stats(V, Fc))
    rep['tiling_error'] = round(abs(rep['white']['volume'] + rep['black']['volume'] - rep['whole']['volume']) / rep['whole']['volume'], 5)
    json.dump(rep, open(os.path.join(a.out, 'report.json'), 'w'), indent=1)
    print(json.dumps(rep))
    return 0


if __name__ == '__main__':
    sys.exit(main())
