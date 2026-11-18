"""Check a candidate test outcome; does not execute repository code."""
import argparse
import hashlib
import json
from pathlib import Path


def assess(exit_code, artifact, expected_sha256=None, blocked_reason=None):
    path = Path(artifact)
    result = {"status": "fail", "exit_code": exit_code, "artifact": str(path)}
    if blocked_reason:
        return dict(result, status="blocked", reason=blocked_reason)
    if exit_code != 0:
        return dict(result, reason="test command failed")
    if not path.is_file() or path.stat().st_size == 0:
        return dict(result, reason="expected nonempty output missing")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    result["sha256"] = digest.hexdigest()
    if expected_sha256 and digest.hexdigest() != expected_sha256.lower():
        return dict(result, reason="artifact checksum mismatch")
    return dict(result, status="pass", reason="output presence and requested hash checks passed; semantic validation still required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--sha256")
    parser.add_argument("--blocked-reason")
    args = parser.parse_args()
    result = assess(args.exit_code, args.artifact, args.sha256, args.blocked_reason)
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "blocked": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
