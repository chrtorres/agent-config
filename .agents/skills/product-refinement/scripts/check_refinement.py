"""Check that a refinement record has the sections needed for a review."""
import argparse
import re
from pathlib import Path

REQUIRED = ("outcome", "baseline", "decisions", "validation", "handoff")


def missing_sections(text):
    sections = re.split(r"^##[ \t]+([^\n]+)\n", text, flags=re.M)
    contents = dict(zip((key.strip().casefold() for key in sections[1::2]), sections[2::2]))
    return [name for name in REQUIRED if not contents.get(name, "").strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    missing = missing_sections(args.record.read_text(encoding="utf-8"))
    print("Missing or empty: " + ", ".join(missing) if missing else "PASS: five review sections have content")
    return bool(missing)


if __name__ == "__main__":
    raise SystemExit(main())
