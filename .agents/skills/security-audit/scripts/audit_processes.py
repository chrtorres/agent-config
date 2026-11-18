#!/usr/bin/env python3
"""Inspect Linux process command lines for credential-bearing arguments safely."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SENSITIVE_FLAG = re.compile(
    r"(?i)(?:api[-_]?key|access[-_]?token|auth(?:orization|[-_]?(?:token|key))|bearer|password|passwd|secret|credential|private[-_]?key|client[-_]?secret)"
)


def command_tokens(raw: bytes) -> list[str]:
    return [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]


def inspect_process(pid: str, cmdline: Path) -> list[dict[str, str]]:
    try:
        tokens = command_tokens(cmdline.read_bytes())
    except OSError:
        return []
    if not tokens:
        return []

    findings = []
    executable = Path(tokens[0]).name or tokens[0]
    for index, token in enumerate(tokens):
        if not token.startswith("-"):
            continue
        flag = token.lstrip("-").split("=", 1)[0]
        if not SENSITIVE_FLAG.search(flag):
            continue
        has_value = "=" in token or index + 1 < len(tokens)
        findings.append(
            {
                "pid": pid,
                "executable": executable,
                "field": flag,
                "category": "process-command-line-credential" if has_value else "credential-flag",
            }
        )
    return findings


def scan_proc(proc_root: Path = Path("/proc")) -> list[dict[str, str]]:
    findings = []
    try:
        entries = sorted(proc_root.iterdir(), key=lambda path: path.name)
    except OSError:
        return findings
    for entry in entries:
        if entry.is_dir() and entry.name.isdigit():
            findings.extend(inspect_process(entry.name, entry / "cmdline"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"), help="procfs root (default: /proc)")
    args = parser.parse_args()
    findings = scan_proc(args.proc_root)
    for finding in findings:
        print(
            f"pid={finding['pid']} executable={finding['executable']} "
            f"field={finding['field']} category={finding['category']}"
        )
    print(f"Scanned process command lines; findings={len(findings)}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
