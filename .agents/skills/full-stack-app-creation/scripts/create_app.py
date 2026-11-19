#!/usr/bin/env python3
"""Create a complete task-local application without overwriting existing work."""
import argparse
import json
from pathlib import Path
import shutil

SKILL = Path(__file__).resolve().parents[1]


def create(destination, example="monitoring"):
    destination = Path(destination).expanduser().absolute()
    if destination.resolve().is_relative_to(SKILL):
        raise ValueError("Choose a task directory outside the shared skill")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; existing work was preserved")
    if example not in {"monitoring", "activity-town", "playable-3d"}:
        raise ValueError(f"Unknown example: {example}")
    source = SKILL / "assets" / ("monitoring-app" if example == "monitoring" else example)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".venv", "evidence"))
    if example == "playable-3d":
        return {"destination": str(destination), "install_command": ["npm", "ci"],
                "build_command": ["npm", "run", "build"],
                "checks_command": ["npm", "run", "smoke", "--", "<fresh-evidence-directory>"],
                "note": "Install Playwright Chromium before smoke checks. Controller input is synthetic."}
    if example == "activity-town":
        return {"destination": str(destination), "install_command": ["npm", "ci"],
                "server_command": ["npm", "run", "dev"],
                "checks_command": ["npm", "run", "smoke", "--", "--evidence", "<fresh-evidence-directory>"],
                "note": "Run from the destination. Smoke checks use synthetic session records."}
    return {"destination": str(destination), "server_command": ["python3", "-B", "server.py"],
            "checks_command": ["python3", "-B", "scripts/run_checks.py", "--output", "<fresh-evidence-directory>", "--browser"],
            "note": "Run from the destination. Browser QA defaults to synthetic data; live inspection requires --live-host."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--example", choices=["monitoring", "activity-town", "playable-3d"], default="monitoring")
    args = parser.parse_args()
    try:
        print(json.dumps(create(args.destination, args.example), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
