#!/usr/bin/env python3
"""Run the acceptance gates in isolated storage; preserve failures and source hashes."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "A01": ("Live inventory", ["backend", "browser"]),
    "A02": ("Filesystem accounting", ["backend"]),
    "A03": ("Unmounted and swap", ["backend"]),
    "A04": ("Truthful SMART states", ["backend", "browser"]),
    "A05": ("Interval I/O", ["backend"]),
    "A06": ("Bounded persistent history", ["backend"]),
    "A07": ("API boundaries", ["backend"]),
    "A08": ("Visual data accuracy", ["browser"]),
    "A09": ("Navigation", ["browser"]),
    "A10": ("Drive inspection", ["browser"]),
    "A11": ("Volume controls", ["browser"]),
    "A12": ("Refresh and pause", ["browser"]),
    "A13": ("Preferences and demo isolation", ["backend", "browser"]),
    "A14": ("Report export", ["backend", "browser"]),
    "A15": ("Capacity thresholds", ["backend"]),
    "A16": ("Empty and failure states", ["backend", "browser"]),
    "A17": ("Stale data and retry", ["browser"]),
    "A18": ("Responsive layout", ["browser"]),
    "A19": ("Keyboard and accessibility", ["browser"]),
    "A20": ("Reproducible evidence", ["runner"]),
}
NONCRITICAL = {"A09", "A10", "A11", "A18"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--live-host", action="store_true", help="Authorize read-only inspection of this Linux host; never opens authentication prompts")
    args = parser.parse_args()
    if not args.live_host:
        parser.error("This full integration suite requires explicit --live-host; see README for fixture-only checks")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT/"evidence"/f"validation-{stamp}").resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(started_at=dt.datetime.now(dt.timezone.utc).isoformat(), cwd=str(ROOT),
                    python=sys.version, platform=platform.platform(), commands=[], hashes={},
                    minimum_acceptance_score=95, score_type="Automated engineering acceptance; human SUS not measured")
    server = None
    temp = tempfile.TemporaryDirectory(prefix="atlas-validation-")
    env = {**os.environ, "ATLAS_EVIDENCE": str(output), "PYTHONDONTWRITEBYTECODE": "1"}
    def command(name, argv, timeout=180):
        started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            code, log = result.returncode, result.stdout+result.stderr
        except (OSError, subprocess.TimeoutExpired) as error:
            code, log = -1, str(error)
        (output/f"{name}.log").write_text(log)
        manifest["commands"].append(dict(name=name, argv=argv, cwd=str(ROOT), exit_code=code,
                                         elapsed_seconds=round(time.monotonic()-started, 3), log=f"{name}.log"))
        print(f"{name}: {'PASS' if code == 0 else 'FAIL'}", flush=True)
        return code == 0
    try:
        command("runtime-versions", ["node", "--version"])
        command("dependencies", ["npm", "ls", "--depth=0"])
        if shutil.which("smartctl"):
            command("smartctl-version", [shutil.which("smartctl"), "--version"])
        command("reference-shell-syntax", ["bash", "-n", "reference/storage-sweep.sh"])
        command("launcher", ["bash", "start.sh", "--help"])
        command("backend", [sys.executable, "-B", "tests/run_backend.py"])
        command("frontend-core", ["node", "tests/core.test.mjs"])
        command("frontend-syntax", ["node", "--check", "web/app.mjs"])
        server_argv = [sys.executable, "-B", "server.py", "--port", "0", "--data-dir", temp.name]
        server = subprocess.Popen(server_argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        with selectors.DefaultSelector() as selector:
            selector.register(server.stdout, selectors.EVENT_READ)
            if not selector.select(15):
                raise RuntimeError("Preview did not announce readiness")
            line = server.stdout.readline().strip()
        if not line.startswith("Atlas storage: http://127.0.0.1:"):
            raise RuntimeError("Unexpected startup: "+line)
        origin = line.removeprefix("Atlas storage: ")
        manifest["server"] = {"argv": server_argv, "url": origin, "isolated_storage": True, "lifecycle": "Stopped by validation runner"}
        command("browser", ["node", "tests/browser.mjs", origin, str(output)])
    except Exception as error:
        manifest["error"] = str(error)
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output/"server.log").write_text(server.stdout.read())
        temp.cleanup()
    for file in sorted(ROOT.rglob("*")):
        relative = file.relative_to(ROOT)
        if not file.is_file() or set(relative.parts) & {"node_modules", "__pycache__", ".runtime", "evidence"}:
            continue
        manifest["hashes"][str(relative)] = hashlib.sha256(file.read_bytes()).hexdigest()
    reports = {}
    for name in ("backend", "browser"):
        file = output/f"{name}-results.json"
        reports[name] = json.loads(file.read_text()) if file.exists() else {}
    runner_ok = (not manifest.get("error") and all(c["exit_code"] == 0 for c in manifest["commands"])
                 and len(reports["browser"].get("screenshots", [])) >= 6 and bool(manifest["hashes"]))
    reports["runner"] = {"scenarios": {"A20": runner_ok}}
    rubric = []
    for code, (label, dependencies) in SCENARIOS.items():
        passed = all(reports[dep].get("scenarios", {}).get(code, False) for dep in dependencies)
        rubric.append(dict(id=code, scenario=label, points=5 if passed else 0, maximum=5,
                           passed=passed, critical=code not in NONCRITICAL, evidence=dependencies))
    score = sum(item["points"] for item in rubric)
    accepted = score >= 95 and runner_ok and all(item["passed"] for item in rubric if item["critical"])
    manifest.update(finished_at=dt.datetime.now(dt.timezone.utc).isoformat(), acceptance_score=score,
                    accepted=accepted, rubric=rubric)
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    lines = [f"# Acceptance result: {score}/100", "", f"Threshold: 95/100. Status: {'PASS' if accepted else 'FAIL'}.", "",
             "Automated engineering acceptance. Human satisfaction and a human SUS score are not measured.", "",
             "| ID | Scenario | Result | Points |", "| --- | --- | --- | --- |"]
    lines.extend(f"| {r['id']} | {r['scenario']} | {'PASS' if r['passed'] else 'FAIL'} | {r['points']}/5 |" for r in rubric)
    lines += ["", "See manifest.json for executed commands, working directories, exit codes, versions, and source hashes. Browser assertions and API traffic are in browser-results.json. Screenshots are settled captures of this application."]
    (output/"ACCEPTANCE.md").write_text("\n".join(lines)+"\n")
    print(f"Acceptance: {score}/100 ({'PASS' if accepted else 'FAIL'}); evidence: {output}")
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
