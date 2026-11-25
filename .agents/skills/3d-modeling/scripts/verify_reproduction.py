"""Verify that a completed modeling project still rebuilds to its approved result.

A project is reproducible on demand when it carries a `reproduce.json` manifest naming a single
entrypoint that regenerates the approved artifacts headlessly, the artifacts that entrypoint must
produce, and the recorded result metrics with tolerances. This verifier runs the entrypoint and
checks the artifacts and metrics, so "recreate that project" is one command whose success is
checked, not asserted. Standard library only.

    python3 verify_reproduction.py <project-dir-or-reproduce.json> [--dry-run] [--timeout S]

--dry-run skips the entrypoint and checks only the artifacts and metrics already on disk (use it to
validate a manifest, or to confirm the currently approved build without a full rebuild).

Manifest schema (paths are relative to the manifest's directory = the project root):

    {
      "project": "name",
      "approved_version": "version-019",
      "entrypoint": {"cmd": ["bash", "version-019/run_build.sh", "repro"],
                     "cwd": ".", "timeout_s": 900,
                     "done_marker": "version-019/logs/repro.done",
                     "marker_ok_regex": "rc=0"},
      "artifacts": [{"path": "version-019/.../model.glb", "min_bytes": 100000}],
      "metrics": {"source": "version-019/trunk_study/study_result.json",
                  "checks": [{"pointer": "F4_strand_map.mean_iou", "min": 0.99}]}
    }

A metric check takes one of `min`, `max`, `equals` (with optional `tol`). A `pointer` walks nested
dict keys / list indices separated by ".".
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time


def load_manifest(arg):
    path = arg if os.path.isfile(arg) else os.path.join(arg, 'reproduce.json')
    if not os.path.isfile(path):
        sys.exit('no reproduce.json at ' + path)
    root = os.path.dirname(os.path.abspath(path))
    return json.load(open(path)), root


def resolve(d, pointer):
    cur = d
    for key in pointer.split('.'):
        if isinstance(cur, list):
            cur = cur[int(key)]
        else:
            cur = cur[key]
    return cur


def run_entrypoint(ep, root, timeout):
    marker = ep.get('done_marker')
    marker_abs = os.path.join(root, marker) if marker else None
    if marker_abs and os.path.exists(marker_abs):
        os.remove(marker_abs)
    cwd = os.path.join(root, ep.get('cwd', '.'))
    t0 = time.time()
    try:
        p = subprocess.run(ep['cmd'], cwd=cwd, timeout=timeout or ep.get('timeout_s', 900),
                           capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return False, 'entrypoint timed out'
    secs = round(time.time() - t0, 1)
    if marker_abs:
        if not os.path.exists(marker_abs):
            return False, f'done marker not written ({marker}); exit {p.returncode}'
        txt = open(marker_abs).read()
        rx = ep.get('marker_ok_regex')
        if rx and not re.search(rx, txt):
            return False, f'marker {marker!r} did not match /{rx}/: {txt.strip()!r}'
        return True, f'entrypoint ok in {secs}s; marker: {txt.strip()}'
    if p.returncode != 0:
        return False, f'entrypoint exit {p.returncode} in {secs}s: {p.stderr[-300:].strip()}'
    return True, f'entrypoint ok in {secs}s'


def check_artifacts(arts, root):
    out = []
    for a in arts:
        f = os.path.join(root, a['path'])
        if not os.path.exists(f):
            out.append((False, a['path'], 'missing'))
            continue
        n = os.path.getsize(f)
        lo = a.get('min_bytes', 1)
        out.append((n >= lo, a['path'], f'{n} bytes' + ('' if n >= lo else f' < {lo}')))
    return out


def check_metrics(spec, root):
    data = json.load(open(os.path.join(root, spec['source'])))
    out = []
    for c in spec.get('checks', []):
        try:
            v = resolve(data, c['pointer'])
        except (KeyError, IndexError, ValueError) as e:
            out.append((False, c['pointer'], f'not found ({e})'))
            continue
        if 'min' in c:
            ok, want = v >= c['min'], f'>= {c["min"]}'
        elif 'max' in c:
            ok, want = v <= c['max'], f'<= {c["max"]}'
        elif 'equals' in c:
            tol = c.get('tol', 0)
            ok, want = abs(v - c['equals']) <= tol, f'== {c["equals"]}±{tol}'
        else:
            ok, want = False, 'no bound (min/max/equals)'
        out.append((ok, c['pointer'], f'{v} ({want})'))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('manifest')
    ap.add_argument('--dry-run', action='store_true', help='skip the entrypoint; check artifacts + metrics on disk')
    ap.add_argument('--timeout', type=int, help='override the entrypoint timeout (seconds)')
    args = ap.parse_args(argv)
    man, root = load_manifest(args.manifest)

    print(f"# reproduce: {man.get('project', '?')} ({man.get('approved_version', '?')})  root={root}")
    rows, ok_all = [], True

    if args.dry_run:
        rows.append(('—', 'entrypoint', 'skipped (--dry-run)'))
    elif 'entrypoint' in man:
        ok, msg = run_entrypoint(man['entrypoint'], root, args.timeout)
        ok_all &= ok
        rows.append(('PASS' if ok else 'FAIL', 'entrypoint', msg))
        if not ok:
            _report(rows)
            return 1

    for ok, name, msg in check_artifacts(man.get('artifacts', []), root):
        ok_all &= ok
        rows.append(('PASS' if ok else 'FAIL', 'artifact ' + name, msg))
    if 'metrics' in man:
        for ok, name, msg in check_metrics(man['metrics'], root):
            ok_all &= ok
            rows.append(('PASS' if ok else 'FAIL', 'metric ' + name, msg))

    _report(rows)
    print('OK' if ok_all else 'FAILED')
    return 0 if ok_all else 1


def _report(rows):
    for status, name, msg in rows:
        print(f'  {status:4}  {name:52}  {msg}')


if __name__ == '__main__':
    sys.exit(main())
