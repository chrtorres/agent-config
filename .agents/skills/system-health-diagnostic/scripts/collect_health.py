#!/usr/bin/env python3
"""Small local read-only baseline; JSON to stdout, no files or privilege escalation."""
import datetime
import json
import subprocess

CHECKS = (
    ('uname', '-a'), ('uptime',), ('free', '-h'),
    ('df', '-hT', '-x', 'squashfs', '-x', 'tmpfs'), ('df', '-i', '/'),
    ('systemctl', '--failed', '--no-pager'),
    ('systemctl', '--user', '--failed', '--no-pager'),
    ('vmstat', '1', '4'), ('sensors',),
    ('journalctl', '-b', '-k', '-p', 'warning', '--no-pager', '-n', '40'),
    ('dpkg', '--audit'), ('ip', '-br', 'address'), ('ip', 'route'),
)


def collect(argv, timeout=12, limit=12000):
    result = dict(argv=list(argv), status='completed', returncode=None,
                  output='', truncated=False)
    try:
        # Fixed argv only; no shell, sudo, network probes, or mutating tools.
        proc = subprocess.run(argv, capture_output=True, text=True,
                              errors='replace', timeout=timeout, check=False)
        result['returncode'] = proc.returncode
        output = proc.stdout + proc.stderr
    except FileNotFoundError:
        result['status'] = 'missing'
        output = 'Command unavailable'
    except subprocess.TimeoutExpired:
        result['status'] = 'timeout'
        output = 'Timed out; no automatic retry'
    result['output'] = output[:limit]
    result['truncated'] = len(output) > limit
    return result


def main():
    print(json.dumps(dict(
        collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        checks=[collect(argv) for argv in CHECKS]), indent=2))


if __name__ == '__main__':
    main()
