"""Copy a reviewed file allowlist into a fresh release directory."""
import argparse
import json
from pathlib import Path
import shutil
import stat
import tempfile


def stage(source, manifest, destination):
    root = source.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Source must be a directory")
    target = destination.parent.resolve(strict=True) / destination.name
    if target.exists() or target.is_symlink() or target.is_relative_to(root):
        raise ValueError("Use a fresh destination outside the source tree")
    listed = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(listed, list) or not listed:
        raise ValueError("Allowlist must be a nonempty JSON array")

    files = {}
    for item in listed:
        if not isinstance(item, str) or not item or "\\" in item or "\x00" in item:
            raise ValueError("Allowlist entries must be relative file paths")
        relative = Path(item)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("Allowlist entries must stay inside the source tree")
        candidate = root
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("Allowlist may only refer to regular files without symlinks")
        mode = candidate.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError("Allowlist may only refer to regular files")
        files[relative] = 0o755 if mode & 0o111 else 0o644

    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".stage-") as directory:
        package = Path(directory) / "package"
        package.mkdir(mode=0o700)
        for relative, mode in files.items():
            output = package / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, output)
            output.chmod(mode)
        # Reserve the destination before publishing the staged directory.
        target.mkdir(mode=0o700)
        try:
            package.rename(target)
        except OSError:
            target.rmdir()
            raise
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "manifest", "destination"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        count = stage(args.source, args.manifest, args.destination)
    except (OSError, ValueError):
        parser.exit(1, "Staging failed. Check the reviewed allowlist, source, and destination.\n")
    print(f"Staged {count} reviewed files.")


if __name__ == "__main__":
    main()
