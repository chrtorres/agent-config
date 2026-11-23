"""Run a build-and-score command over a grid of parameter overrides and rank the results.

    python3 sweep_params.py --grid grid.json --command "<cmd with {params} and {tag}>" \
        --out <dir> --score <key> [--baseline override.json] [--maximize|--minimize]

grid.json maps dotted parameter paths to candidate values, for example
    {"saddle.xR_top": [7.3, 8.0], "saddle.lobe_drop": [3.0, 4.5]}
Every combination is written as a nested override file <out>/<tag>.json, then the command runs with {params}
replaced by that file and {tag} by a short identifier. The command must print a JSON object on its last stdout
line (for example the scorer's metrics); the run fails loudly otherwise.

Results go to <out>/sweep.json and a ranked table on stdout. The output labels the winning score as a FIT score:
the parameters were chosen on the same data that produced it, so it is not an independent test. Score a holdout
view or frame separately before claiming a likeness improvement.
"""
import argparse, itertools, json, os, shlex, subprocess, sys


def nested(dotted):
    out = {}
    for path, value in dotted.items():
        cur = out; keys = path.split('.')
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = value
    return out


def merge(a, b):
    """Deep-merge b into a copy of a (b wins)."""
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def combos(grid):
    keys = sorted(grid)
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))


def tag_for(i, combo):
    return f's{i:03d}'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grid', required=True); ap.add_argument('--command', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--score', required=True)
    ap.add_argument('--baseline', help='override JSON merged under every combination')
    g = ap.add_mutually_exclusive_group(); g.add_argument('--maximize', action='store_true', default=True)
    g.add_argument('--minimize', action='store_true')
    a = ap.parse_args(argv)
    grid = json.load(open(a.grid)); base = json.load(open(a.baseline)) if a.baseline else {}
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for i, combo in enumerate(combos(grid)):
        tag = tag_for(i, combo); pfile = os.path.join(a.out, f'{tag}.json')
        json.dump(merge(base, nested(combo)), open(pfile, 'w'), indent=1)
        cmd = a.command.replace('{params}', shlex.quote(pfile)).replace('{tag}', tag)
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines = [ln for ln in r.stdout.strip().splitlines() if ln.strip()]
        if r.returncode != 0 or not lines:
            sys.stderr.write(f'{tag} failed (exit {r.returncode}):\n{r.stderr[-2000:]}\n'); return 2
        try:
            metrics = json.loads(lines[-1])
        except json.JSONDecodeError:
            sys.stderr.write(f'{tag}: last stdout line is not JSON: {lines[-1][:200]}\n'); return 2
        if a.score not in metrics:
            sys.stderr.write(f'{tag}: score key {a.score!r} missing from {sorted(metrics)}\n'); return 2
        rows.append(dict(tag=tag, params=combo, metrics=metrics))
        print(f'{tag} {json.dumps(combo)} {a.score}={metrics[a.score]}', flush=True)
    sign = -1 if a.minimize else 1
    rows.sort(key=lambda r: sign * r['metrics'][a.score], reverse=True)
    best = rows[0]
    res = dict(score=a.score, direction='minimize' if a.minimize else 'maximize', runs=rows, best=best,
               note='best score is a FIT score on the data used for selection; verify on a holdout before claiming improvement')
    json.dump(res, open(os.path.join(a.out, 'sweep.json'), 'w'), indent=1)
    print(f'best {best["tag"]} {json.dumps(best["params"])} {a.score}={best["metrics"][a.score]} (fit score, not a holdout)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
