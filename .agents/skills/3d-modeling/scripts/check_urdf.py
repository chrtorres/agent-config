"""Standard-library consistency checks for a generated URDF robot description.

    python3 check_urdf.py <robot.urdf> [--package-root <dir>] [--expect <expect.json>]

Always checks: a single-rooted link tree; every joint names existing links; joint
types; unit axes on moving joints; ordered limits on revolute/prismatic joints;
visual/collision mesh files resolve (package://<pkg>/ maps to --package-root, else the
URDF's directory); every inertial has positive mass and a positive-definite inertia
tensor satisfying the triangle inequality (Ixx + Iyy >= Izz and permutations).

--expect is an optional JSON file of project-specific acceptance values:

    {"total_mass_kg": [3.85, 0.01],                  # value, tolerance
     "frames": {"<link>": {"xyz": [x, y, z], "rpy": [r, p, y]}},   # FK from root, tol 1e-6
     "min_z": {"<link>": [<radius_m>, 1e-4]},       # wheel contact: link z - radius ~ 0
     "support_polygon": ["<link>", ...]}            # mass-weighted COM xy inside these links' xy

Prints PASS/FAIL per check and exits 1 on any failure. Use an independent parser
(for example yourdfpy) as a second opinion; this script does not replace it.
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def vec(text, default="0 0 0"):
    return [float(v) for v in (text or default).split()]


def rpy_matrix(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def matrix_rpy(m):
    pitch = math.asin(max(-1.0, min(1.0, -m[2][0])))
    return [math.atan2(m[2][1], m[2][2]), pitch, math.atan2(m[1][0], m[0][0])]


def det3(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def origin(el):
    o = el.find("origin") if el is not None else None
    return (vec(o.get("xyz")) if o is not None else [0, 0, 0],
            vec(o.get("rpy")) if o is not None else [0, 0, 0])


def run(urdf, package_root=None, expect=None):
    results = []

    def check(ok, label):
        results.append((bool(ok), label))

    root = ET.parse(urdf).getroot()
    links = {l.get("name"): l for l in root.findall("link")}
    joints = root.findall("joint")
    children = {j.find("child").get("link") for j in joints}
    roots = [n for n in links if n not in children]
    check(len(roots) == 1, f"single root link ({roots})")
    check(all(j.find("parent").get("link") in links and j.find("child").get("link") in links for j in joints),
          "every joint names existing parent and child links")
    check(len(children) == len(joints), "no link has two parent joints")
    types = {"fixed", "continuous", "revolute", "prismatic", "floating", "planar"}
    check(all(j.get("type") in types for j in joints), "joint types are valid")
    for j in joints:
        if j.get("type") in ("continuous", "revolute", "prismatic"):
            axis = vec(j.find("axis").get("xyz") if j.find("axis") is not None else "1 0 0")
            check(abs(math.sqrt(sum(a * a for a in axis)) - 1) < 1e-6, f"{j.get('name')}: unit axis")
        if j.get("type") in ("revolute", "prismatic"):
            lim = j.find("limit")
            check(lim is not None and float(lim.get("lower", 0)) < float(lim.get("upper", 0)),
                  f"{j.get('name')}: ordered limits")

    base = Path(package_root) if package_root else Path(urdf).parent
    for mesh in root.iter("mesh"):
        name = mesh.get("filename")
        rel = name.split("://", 1)[1].split("/", 1)[1] if name.startswith("package://") else name
        check((base / rel).is_file(), f"mesh resolves: {name}")

    masses, coms = {}, {}
    for name, link in links.items():
        inertial = link.find("inertial")
        if inertial is None:
            continue
        mass = float(inertial.find("mass").get("value"))
        i = inertial.find("inertia")
        g = {k: float(i.get(k, 0)) for k in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")}
        t = [[g["ixx"], g["ixy"], g["ixz"]], [g["ixy"], g["iyy"], g["iyz"]], [g["ixz"], g["iyz"], g["izz"]]]
        minors = [t[0][0], t[0][0] * t[1][1] - t[0][1] ** 2, det3(t)]
        check(mass > 0, f"{name}: positive mass")
        check(all(m > 0 for m in minors), f"{name}: positive-definite inertia")
        d = (g["ixx"], g["iyy"], g["izz"])
        check(all(d[a] + d[b] >= d[c] - 1e-12 for a, b, c in ((0, 1, 2), (1, 2, 0), (0, 2, 1))),
              f"{name}: inertia triangle inequality")
        masses[name], coms[name] = mass, origin(inertial)[0]

    # Forward kinematics at zero joint positions.
    pose = {roots[0]: ([0.0, 0.0, 0.0], [[1, 0, 0], [0, 1, 0], [0, 0, 1]])} if len(roots) == 1 else {}
    pending = list(joints)
    while pending:
        progressed = False
        for j in list(pending):
            parent, child = j.find("parent").get("link"), j.find("child").get("link")
            if parent in pose:
                p, r = pose[parent]
                xyz, rpy = origin(j)
                pose[child] = ([a + b for a, b in zip(p, apply(r, xyz))], matmul(r, rpy_matrix(*rpy)))
                pending.remove(j)
                progressed = True
        if not progressed:
            check(False, "joint tree is connected for FK")
            break

    expect = expect or {}
    if "total_mass_kg" in expect:
        value, tol = expect["total_mass_kg"]
        check(abs(sum(masses.values()) - value) <= tol, f"total mass {sum(masses.values()):.4f} kg ~ {value}")
    for name, want in expect.get("frames", {}).items():
        got = pose.get(name)
        check(got and all(abs(a - b) < 1e-6 for a, b in zip(got[0], want["xyz"])), f"{name}: position")
        if got and "rpy" in want:
            # Compare rotation matrices so equivalent rpy triples are not false failures.
            err = max(abs(a - b) for ra, rb in zip(got[1], rpy_matrix(*want["rpy"])) for a, b in zip(ra, rb))
            check(err < 1e-6, f"{name}: orientation")
    for name, (radius, tol) in expect.get("min_z", {}).items():
        z = pose[name][0][2] - radius if name in pose else None
        check(z is not None and abs(z) <= tol, f"{name}: touches z=0 (lowest point {z})")
    support = expect.get("support_polygon")
    if support and masses:
        total = sum(masses.values())
        com = [sum(masses[n] * (pose[n][0][k] + apply(pose[n][1], coms[n])[k]) for n in masses) / total
               for k in range(2)]
        pts = [pose[n][0][:2] for n in support]
        signs = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            signs.append((b[0] - a[0]) * (com[1] - a[1]) - (b[1] - a[1]) * (com[0] - a[0]))
        check(all(s > 0 for s in signs) or all(s < 0 for s in signs),
              f"COM xy {[round(c, 4) for c in com]} inside support polygon")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urdf")
    parser.add_argument("--package-root")
    parser.add_argument("--expect", type=Path)
    args = parser.parse_args()
    expect = json.loads(args.expect.read_text()) if args.expect else None
    results = run(args.urdf, args.package_root, expect)
    for ok, label in results:
        print(f"{'PASS' if ok else 'FAIL'} {label}")
    failed = sum(not ok for ok, _ in results)
    print(f"{len(results) - failed}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
