# Generalized interactive-review smoke testing

Use `scripts/run_interactive_review_smoke.py` to validate the required viewer in a retained sandbox. The runner creates synthetic Blender models, renders shadows, exports GLB files, copies the portable viewer, serves the sandbox over HTTP, checks delivery endpoints, and uses a Chromium-compatible browser to produce screenshots.

## Run

```sh
python3 <skill-dir>/scripts/run_interactive_review_smoke.py \
  --sandbox <workspace-root>/creations/smoke-test/<run-id>
```

The default matrix has six shapes (`cube`, `sphere`, `cylinder`, `cone`, `torus`, `ico`) and six shadow styles (`soft`, `left`, `right`, `rim`, `top`, `cross`). It normally produces more than 20 checks. Use `--min-checks` to raise the required threshold, not lower it below the workflow's acceptance requirement.

## What it teaches and verifies

- A rendered PNG proves only that a scene rendered; the browser GLB viewer must also load.
- HTTP serving is part of the contract because browser `file://` security can block module and GLB requests.
- Multiple silhouettes and lighting directions reveal viewer framing, normals, material, and shadow problems that one test shape can hide.
- The evidence set should include source/build logs, `.blend`, PNG, GLB, metadata, browser screenshot, and an individual result line for every check.
- A passing viewer smoke test does not prove mesh validity, printability, dimensional accuracy, strength, or load capacity.

## Cleanup boundary

The runner writes a marker into the sandbox and never deletes it during a normal run. Cleanup requires a separate, explicit command after user approval:

```sh
python3 <skill-dir>/scripts/run_interactive_review_smoke.py \
  --sandbox <same-sandbox> --cleanup-approved
```

The cleanup flag requires the marker and safe-path checks. Keep the evidence until the user approves cleanup.

## Stopping a review server safely

When you launch the viewer or a smoke server yourself (for example on a spare port) and need to stop it, do not run `pkill -f <pattern>` or `for p in $(pgrep -f <pattern>)` in a shell command whose own text contains that pattern: `-f` matches the full command line, so it matches and kills the calling shell (exit 144), silently aborting anything queued after it. List the PID with a bracket-grep that cannot match itself, then kill it in a separate call, and confirm the port is released:

```sh
ps -eo pid,args | grep -E "[l]aunch_interactive_viewer"   # the bracket avoids self-match
kill <pid>
ss -ltnp | grep <port> || echo "released"
```

Stop any server you start as soon as the review is captured, and leave the user's own preview servers alone.
