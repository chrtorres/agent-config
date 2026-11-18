#!/usr/bin/env python3
"""Journal already-reviewed Fastboot getvar queries; never discover, retry or mutate."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess

ALLOWED = frozenset(('product', 'version-bootloader', 'device-state', 'secureboot',
                     'boot-state', 'unlocked', 'secure', 'max-download-size'))
REQUIRED = frozenset(('product', 'version-bootloader', 'device-state', 'secureboot'))

class StopTest(RuntimeError):
    pass


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {'serial', 'baseline', 'queries'}:
        raise ValueError('Plan requires only serial, baseline and queries.')
    serial = plan['serial']
    if not isinstance(serial, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*', serial):
        raise ValueError('Use one explicit serial, not options or transport discovery.')
    baseline = plan['baseline']
    if not isinstance(baseline, dict) or not REQUIRED <= baseline.keys():
        raise ValueError('Missing identity/security baseline fields.')
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in baseline.items()):
        raise ValueError('Baseline keys and values must be strings.')
    if any(not baseline[k] for k in REQUIRED):
        raise ValueError('Required identity/security fields cannot be empty.')
    if 'serialno' in baseline and baseline['serialno'] != serial:
        raise ValueError('Baseline serial differs from selected serial.')
    if not isinstance(plan['queries'], list) or not plan['queries']:
        raise ValueError('Supply at least one previously reviewed query.')
    for q in plan['queries']:
        if not isinstance(q, dict) or set(q) != {'key', 'expected'}:
            raise ValueError('Query requires only key and expected.')
        if not isinstance(q['key'], str) or q['key'] not in ALLOWED:
            raise ValueError('Unreviewed query: outside fixed getvar allowlist.')
        if not isinstance(q['expected'], str) or not q['expected']:
            raise ValueError('Query expected value must be a nonempty string.')
        if q['key'] in baseline and q['expected'] != baseline[q['key']]:
            raise ValueError('Query expectation contradicts baseline.')


def parse_state(text):
    result = {}
    for line in text.splitlines():
        match = re.fullmatch(r'\(bootloader\) ([^\r\n]+?): (.*)', line)
        if match:
            k, v = match.groups()
            if k in result:
                raise StopTest('Duplicate field in state report; preserve raw output.')
            result[k] = v
    if not REQUIRED <= result.keys():
        raise StopTest('State report missing required identity/security fields.')
    return result


def run(plan, executable, output, runner=subprocess.run):
    validate(plan)
    if not os.path.isabs(str(executable)):
        raise ValueError('Select an absolute path to a reviewed Fastboot executable.')
    with Path(output).open('x', encoding='utf-8') as journal:
        def call(key, role):
            cmd = [str(executable), '-s', plan['serial'], 'getvar', key]
            record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'command': cmd, 'role': role}
            try:
                p = runner(cmd, capture_output=True, text=True, timeout=15,
                           stdin=subprocess.DEVNULL)
                record.update(exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
            except subprocess.TimeoutExpired as e:
                def decoded(value):
                    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
                record.update(exit=None, timeout=True, stdout=decoded(e.stdout), stderr=decoded(e.stderr))
            except OSError as e:
                record.update(exit=None, host_error=str(e), stdout='', stderr='')
            journal.write(json.dumps(record, ensure_ascii=True) + '\n')
            journal.flush()
            if record['exit'] != 0:
                raise StopTest('Failed command or timeout; no further device operation.')
            return record['stdout'] + record['stderr']

        first = parse_state(call('all', 'baseline'))
        if any(first.get(k) != v for k, v in plan['baseline'].items()):
            raise StopTest('Baseline differs from reviewed expected state.')
        if 'serialno' in first and first['serialno'] != plan['serial']:
            raise StopTest('Reported serial differs from selected serial.')
        for q in plan['queries']:
            if parse_state(call('all', 'before')) != first:
                raise StopTest('State changed before query; stop.')
            response = call(q['key'], 'query')
            lines = [line for line in response.splitlines()
                     if line.startswith(q['key'] + ':')]
            if lines != [q['key'] + ': ' + q['expected']]:
                raise StopTest('Unexpected query response; do not issue post-query commands.')
            if parse_state(call('all', 'after')) != first:
                raise StopTest('State changed after query; stop.')
    return 1 + 3 * len(plan['queries'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--fastboot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ack-reviewed-authorized-read-only', action='store_true', required=True)
    args = parser.parse_args()
    try:
        count = run(json.loads(args.plan.read_text()), args.fastboot, args.output)
    except (StopTest, ValueError, OSError) as e:
        parser.exit(1, 'STOP: ' + str(e) + '\n')
    print(f'Completed {count} getvar calls with unchanged reported state. No storage-integrity claim.')

if __name__ == '__main__':
    main()
