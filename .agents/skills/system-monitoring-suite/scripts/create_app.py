#!/usr/bin/env python3
"""Create a complete task-local application without overwriting existing work."""
import argparse
import json
from pathlib import Path
import shutil

SKILL = Path(__file__).resolve().parents[1]


def create(destination):
    destination = Path(destination).expanduser().absolute()
    if destination.resolve().is_relative_to(SKILL):
        raise ValueError("Choose a task directory outside the shared skill")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; existing work was preserved")
    source = SKILL / "assets" / "monitoring-app"
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".venv", "evidence"))
    return {"destination": str(destination), "server_command": ["python3", "-B", "server.py"],
            "checks_command": ["python3", "-B", "scripts/run_checks.py", "--output", "<fresh-evidence-directory>", "--browser"],
            "note": "Run from the destination. Browser QA defaults to synthetic data; live inspection requires --live-host."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(create(args.destination), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
