#!/usr/bin/env python3
"""Create a streaming SHA-256 manifest; never follow symlinks or overwrite files."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Evidence root must be a real directory, not a symlink.')
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(list(dirs) + files):
            p = Path(parent) / name
            label = p.relative_to(root).as_posix()
            if p.is_symlink():
                result.append({'path': label, 'kind': 'symlink', 'target': os.readlink(p)})
            elif p.is_file():
                digest = hashlib.sha256()
                with p.open('rb') as f:
                    for block in iter(lambda: f.read(1024 * 1024), b''):
                        digest.update(block)
                result.append({'path': label, 'kind': 'file', 'bytes': p.stat().st_size,
                               'sha256': digest.hexdigest()})
    return sorted(result, key=lambda r: r['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output exists; never overwrite evidence or an earlier manifest.')
    try:
        entries = inventory(args.root)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump({'algorithm': 'sha256', 'entries': entries}, f, indent=2)
            f.write('\n')
    except (OSError, ValueError) as e:
        parser.exit(1, str(e) + '\n')

if __name__ == '__main__':
    main()
