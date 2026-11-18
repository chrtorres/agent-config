"""Preflight and create missing model-discovery directory links."""
import argparse
import json
import os
from pathlib import Path
import re


def skill_name(skill):
    content = (skill / 'SKILL.md').read_text()
    match = re.match(r'^---\n(.*?)\n---(?:\n|$)', content, re.S)
    if not match:
        raise ValueError('Missing skill frontmatter')
    name = re.search(r'^name:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$', match.group(1), re.M)
    if not name or name.group(1) != skill.name or len(skill.name) > 64:
        raise ValueError('Unquoted frontmatter name must match the lowercase skill directory name')
    return name.group(1)


def link_skill(skill, discoveries, apply=False):
    # Preserve the selected canonical spelling for links; resolve only for identity checks.
    skill = Path(skill).absolute()
    name = skill_name(skill)
    plans = []
    for directory in dict.fromkeys(Path(d).absolute() for d in discoveries):
        if directory.exists() and not directory.is_dir():
            raise ValueError('Discovery parent is not a directory: ' + str(directory))
        link = directory / name
        if link == skill or (link.exists() and os.path.samefile(link, skill)):
            action = 'existing'
        elif os.path.lexists(link):
            raise ValueError('Discovery conflict preserved: ' + str(link))
        else:
            action = 'create'
        plans.append({'path': str(link), 'action': action})
    # No writes occur until every destination passes preflight.
    if apply:
        for plan in plans:
            link = Path(plan['path'])
            if plan['action'] == 'create':
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(skill, target_is_directory=True)
            if not os.path.samefile(link, skill) or not (link / 'SKILL.md').is_file():
                raise ValueError('Discovery verification failed: ' + str(link))
    return {'applied': apply, 'links': plans}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill', type=Path)
    parser.add_argument('--discovery', action='append', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(link_skill(args.skill, args.discovery, args.apply), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'applied': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
