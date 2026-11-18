"""Synthetic-only tests. Never invokes a real device, Fastboot or analysis engine."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE/'scripts'/(name+'.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
queries = module('record_queries')
hashes = module('hash_evidence')
PLAN = {'serial': 'SIMULATED-UNIT', 'baseline': {
    'product': 'simulated', 'version-bootloader': 'test-only',
    'device-state': 'locked', 'secureboot': 'yes'},
    'queries': [{'key': 'product', 'expected': 'simulated'}]}
def state(change=None):
    values = dict(PLAN['baseline'], serialno=PLAN['serial'])
    if change: values.update(change)
    return ''.join(f'(bootloader) {k}: {v}\n' for k,v in values.items())

class QueryTests(unittest.TestCase):
    def simulate(self, responses, plan=None):
        self.calls = []
        def fake(cmd, **kwargs):
            self.calls.append(cmd)
            response = responses[len(self.calls)-1]
            if isinstance(response, Exception): raise response
            code, text = response
            return subprocess.CompletedProcess(cmd, code, '', text)
        return queries.run(plan or PLAN, '/reviewed/fastboot', self.output, fake)
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)/'journal.jsonl'
    def records(self):
        return [json.loads(s) for s in self.output.read_text().splitlines()]
    def test_success_and_exact_commands(self):
        self.assertEqual(self.simulate([(0,state()), (0,state()), (0,'product: simulated\n'), (0,state())]),4)
        self.assertEqual([x[-1] for x in self.calls], ['all','all','product','all'])
        self.assertTrue(all(x[:4] == ['/reviewed/fastboot','-s','SIMULATED-UNIT','getvar'] for x in self.calls))
        self.assertEqual([r['role'] for r in self.records()],['baseline','before','query','after'])
    def test_security_change_stops_before_query(self):
        with self.assertRaises(queries.StopTest):
            self.simulate([(0,state()), (0,state({'device-state':'unlocked'}))])
        self.assertEqual(len(self.calls),2)
    def test_unexpected_response_stops_without_postcheck(self):
        with self.assertRaises(queries.StopTest):
            self.simulate([(0,state()),(0,state()),(0,'product: unexpected\n')])
        self.assertEqual(len(self.calls),3)
    def test_failure_preserved_and_no_retry(self):
        with self.assertRaises(queries.StopTest): self.simulate([(1,'permission denied\n')])
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.records()[0]['exit'],1)
    def test_timeout_preserved_and_no_recovery(self):
        error=subprocess.TimeoutExpired(['simulated'],15,output=b'partial',stderr=b'waiting')
        with self.assertRaises(queries.StopTest):self.simulate([error])
        self.assertEqual(len(self.calls),1)
        self.assertTrue(self.records()[0]['timeout'])
        self.assertEqual(self.records()[0]['stdout'],'partial')
    def test_refuses_mutation_plan_before_device_call(self):
        plan=copy.deepcopy(PLAN);plan['queries'][0]['key']='reboot'
        with self.assertRaises(ValueError):self.simulate([],plan)
        self.assertEqual(self.calls,[])
        self.assertFalse(self.output.exists())
    def test_no_journal_overwrite(self):
        self.output.write_text('original')
        with self.assertRaises(FileExistsError):self.simulate([])
        self.assertEqual(self.calls,[])
        self.assertEqual(self.output.read_text(),'original')
    def test_duplicate_report_field_stops(self):
        with self.assertRaises(queries.StopTest):
            self.simulate([(0,state()+'(bootloader) product: other\n')])
        self.assertEqual(len(self.calls),1)
    def test_wrong_serial_stops(self):
        with self.assertRaises(queries.StopTest):self.simulate([(0,state({'serialno':'OTHER'}))])
        self.assertEqual(len(self.calls),1)

class HashTests(unittest.TestCase):
    def test_hashes_bytes_and_does_not_follow_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'evidence';root.mkdir()
            outside=Path(tmp)/'outside';outside.mkdir();(outside/'hidden').write_bytes(b'not evidence')
            data=b'known contents\x00'*(100000)
            (root/'image').write_bytes(data)
            (root/'linked-dir').symlink_to(outside,target_is_directory=True)
            (root/'linked-file').symlink_to(outside/'hidden')
            rows={r['path']:r for r in hashes.inventory(root)}
            self.assertEqual(set(rows),{'image','linked-dir','linked-file'})
            self.assertEqual(rows['image']['sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(rows['image']['bytes'],len(data))
            self.assertEqual(rows['linked-dir']['kind'],'symlink')
    def test_refuses_link_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'link').symlink_to(p,target_is_directory=True)
            with self.assertRaises(ValueError):hashes.inventory(p/'link')

if __name__ == '__main__':unittest.main()
