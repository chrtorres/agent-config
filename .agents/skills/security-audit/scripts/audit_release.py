#!/usr/bin/env python3
"""Scan release trees and archives for common secrets and private identity data."""
from __future__ import annotations

import argparse
import re
import sys
import tarfile
from pathlib import Path


PATTERNS = (
    ("secret", re.compile(r"(?i)\b(?:api[_ -]?key|secret|password|passwd|bearer|authorization)\b\s*[:=]\s*[\"']?([^\s\"',}\]]+)")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("home-path", re.compile(r"(?:/home/[^/\s\"']+|/Users/[^/\s\"']+|[A-Za-z]:\\Users\\[^\\\s\"']+)")),
    ("media-user-path", re.compile(r"/media/[^/\s\"']+")),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.I)),
    ("pid", re.compile(r"\"(?:pid|process_id)\"\s*:\s*\d+")),
)
SKIP_PARTS = {".git", ".runtime", "node_modules", "__pycache__", ".venv", "venv"}
MAX_TEXT_BYTES = 4 * 1024 * 1024


def scan_text(name: str, raw: bytes) -> list[dict[str, object]]:
    if len(raw) > MAX_TEXT_BYTES or b"\x00" in raw[:8192]:
        return []
    text = raw.decode("utf-8", errors="replace")
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for category, pattern in PATTERNS:
            match = pattern.search(line)
            if match and not (category == "secret" and match.group(1).lower() in {"no", "none", "null", "false", "example", "test"}):
                findings.append({"file": name, "line": number, "category": category})
    return findings


def scan_root(root: Path) -> list[dict[str, object]]:
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        findings.extend(scan_text(str(path.relative_to(root)), path.read_bytes()))
    return findings


def scan_archive(archive: Path) -> list[dict[str, object]]:
    findings = []
    with tarfile.open(archive, "r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile() or any(part in SKIP_PARTS for part in Path(member.name).parts):
                continue
            stream = tar.extractfile(member)
            if stream:
                findings.extend(scan_text(f"{archive.name}:{member.name}", stream.read(MAX_TEXT_BYTES + 1)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    findings = scan_root(args.root.resolve())
    if args.archive:
        findings.extend(scan_archive(args.archive.resolve()))
    for finding in findings:
        print(f"{finding['file']}:{finding['line']}: {finding['category']}")
    print(f"Scanned; findings={len(findings)}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
