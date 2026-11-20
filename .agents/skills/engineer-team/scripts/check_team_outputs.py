#!/usr/bin/env python3
"""Check that an engineer-team planning round produced complete outputs.

Usage:
    python3 check_team_outputs.py <plan-dir> [--roles ux-research,visual-design,...] [--no-pm] [--json]

Checks (each reported pass/fail):
  - every expected role plan file `NN-<role>.md` exists and is non-trivial
  - each role plan contains a "Top 5 priorities" heading
  - the PM synthesis `00-pm-synthesis.md` exists and has the required sections
  - TEAM-BRIEF.md exists
Exit status 0 when all checks pass, 1 otherwise, 2 on usage errors.
Read-only: never modifies the plan directory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_ROLES = [
    "ux-research",
    "visual-design",
    "frontend-engineering",
    "design-systems",
    "motion-design",
    "qa-plan",
]
MIN_BYTES = 400
TOP5 = re.compile(r"^#{1,6}\s*(\d+\.\s*)?top\s*(5|five)\s+priorities\b", re.I | re.M)
PM_SECTIONS = {
    "outcome": re.compile(r"^#{1,6}\s*(\d+\.\s*)?outcome\b", re.I | re.M),
    "decisions": re.compile(r"^#{1,6}\s*(\d+\.\s*)?decisions?\b", re.I | re.M),
    "scope": re.compile(r"^#{1,6}\s*(\d+\.\s*)?scope\b", re.I | re.M),
    "p0": re.compile(r"\bP0\b"),
    "implementation sequence": re.compile(r"^#{1,6}\s*(\d+\.\s*)?(implementation sequence|milestones)\b", re.I | re.M),
    "definition of done": re.compile(r"^#{1,6}\s*(\d+\.\s*)?definition of done\b", re.I | re.M),
    "risks": re.compile(r"^#{1,6}\s*(\d+\.\s*)?(open\s+)?risks\b", re.I | re.M),
    "top 5": TOP5,
}


def find_role_file(plan_dir: Path, role: str) -> Path | None:
    matches = sorted(plan_dir.glob(f"[0-9][0-9]-{role}.md"))
    return matches[0] if matches else None


def check(plan_dir: Path, roles: list[str], require_pm: bool) -> list[dict]:
    results: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})

    add("team-brief exists", (plan_dir / "TEAM-BRIEF.md").is_file(), "TEAM-BRIEF.md")
    for role in roles:
        f = find_role_file(plan_dir, role)
        add(f"{role}: file exists", f is not None, f.name if f else f"NN-{role}.md missing")
        if f is None:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        add(f"{role}: non-trivial", len(text.encode()) >= MIN_BYTES, f"{len(text.encode())} bytes")
        add(f"{role}: top 5 priorities", bool(TOP5.search(text)))
    if require_pm:
        pm = plan_dir / "00-pm-synthesis.md"
        add("pm: file exists", pm.is_file(), pm.name)
        if pm.is_file():
            text = pm.read_text(encoding="utf-8", errors="replace")
            for name, rx in PM_SECTIONS.items():
                add(f"pm: {name}", bool(rx.search(text)))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_dir", type=Path)
    ap.add_argument("--roles", default=",".join(DEFAULT_ROLES), help="comma-separated role slugs")
    ap.add_argument("--no-pm", action="store_true", help="skip PM synthesis checks (mid-round)")
    ap.add_argument("--json", action="store_true", help="print JSON results")
    args = ap.parse_args(argv)
    if not args.plan_dir.is_dir():
        print(f"not a directory: {args.plan_dir}", file=sys.stderr)
        return 2
    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    results = check(args.plan_dir, roles, not args.no_pm)
    passed = sum(r["pass"] for r in results)
    if args.json:
        print(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2))
    else:
        for r in results:
            print(f"{'PASS' if r['pass'] else 'FAIL'}  {r['check']}" + (f"  ({r['detail']})" if r["detail"] else ""))
        print(f"{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
