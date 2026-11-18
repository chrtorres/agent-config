#!/usr/bin/env python3
"""Copy the optional storage example outside the shared skill without overwriting."""
import argparse
from pathlib import Path
import shutil

SKILL = Path(__file__).resolve().parents[1]


def create(destination):
    destination = Path(destination).expanduser().absolute()
    if destination.resolve().is_relative_to(SKILL):
        raise ValueError("Destination must be outside the shared skill")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination exists; existing work preserved")
    shutil.copytree(SKILL / "assets/storage-app", destination,
                    ignore=shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", ".runtime", "evidence"))
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(create(args.destination))
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
