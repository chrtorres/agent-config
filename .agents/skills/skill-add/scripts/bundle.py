"""Index and verify a skill's portable resource tree. Standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


IGNORED_NAMES = {'.git', 'node_modules', '__pycache__', '.venv'}
DEFAULT_MANIFEST = 'references/bundle-index.json'


def local_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Expected a non-escaping relative resource path')
    result = root / path
    if not result.resolve().is_relative_to(root):
        raise ValueError('Resource resolves outside the skill')
    return result


def inventory(root, manifest=DEFAULT_MANIFEST):
    root = Path(root).resolve()
    if not (root / 'SKILL.md').is_file():
        raise ValueError('Skill entrypoint not found')
    index_path = local_path(root, manifest)
    entries = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in IGNORED_NAMES)
        for name in sorted(directories + files):
            if name in IGNORED_NAMES:
                continue
            path = Path(parent) / name
            if path == index_path:
                continue
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                target = os.readlink(path)
                if Path(target).is_absolute():
                    raise ValueError('Absolute internal symlink is not portable: ' + relative)
                resolved = path.resolve()
                if not resolved.is_relative_to(root) or not resolved.exists():
                    raise ValueError('Escaping or dangling symlink: ' + relative)
                entries[relative] = {'type': 'symlink', 'target': target}
            elif stat.S_ISDIR(mode):
                entries[relative] = {'type': 'directory'}
            elif stat.S_ISREG(mode):
                data = path.read_bytes()
                entries[relative] = {'type': 'file', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                     'executable': bool(mode & stat.S_IXUSR)}
            else:
                raise ValueError('Unsupported special filesystem object: ' + relative)
    return dict(sorted(entries.items()))


def write_index(root, manifest=DEFAULT_MANIFEST):
    root = Path(root).resolve()
    path = local_path(root, manifest)
    if path.is_symlink():
        raise ValueError('Manifest must not be a symlink')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create the manifest parent before indexing so a fresh index verifies itself.
    result = {'format_version': 1, 'scope': 'Resource identity snapshot, not semantic or security validation',
              'ignored_entry_names': sorted(IGNORED_NAMES), 'entries': inventory(root, manifest)}
    path.write_text(json.dumps(result, indent=2) + '\n')
    return result


def verify(root, manifest=DEFAULT_MANIFEST):
    root = Path(root).resolve()
    path = local_path(root, manifest)
    if path.is_symlink():
        raise ValueError('Manifest must not be a symlink')
    expected = json.loads(path.read_text())
    if expected.get('format_version') != 1 or expected.get('ignored_entry_names') != sorted(IGNORED_NAMES):
        raise ValueError('Unsupported manifest format or exclusion policy')
    entries = expected.get('entries')
    if not isinstance(entries, dict):
        raise ValueError('Manifest entries must be an object')
    for relative in entries:
        local_path(root, relative)
    actual = inventory(root, manifest)
    missing = sorted(entries.keys() - actual.keys())
    extra = sorted(actual.keys() - entries.keys())
    changed = sorted(p for p in entries.keys() & actual.keys() if entries[p] != actual[p])
    return {'passed': not (missing or extra or changed), 'missing': missing, 'extra': extra, 'changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['index', 'verify'])
    parser.add_argument('skill', type=Path)
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        if args.action == 'index':
            result = write_index(args.skill, args.manifest)
            print(json.dumps({'indexed_entries': len(result['entries']), 'manifest': args.manifest}))
            return 0
        result = verify(args.skill, args.manifest)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
