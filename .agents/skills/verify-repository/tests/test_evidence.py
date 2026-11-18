import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_evidence", ROOT / "scripts/check_evidence.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class EvidenceTests(unittest.TestCase):
    def test_zero_exit_missing_report_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(m.assess(0, Path(directory)/"missing")["status"], "fail")

    def test_empty_report_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"empty";p.touch()
            self.assertEqual(m.assess(0,p)["status"],"fail")

    def test_valid_fixture_and_hash(self):
        p=ROOT/"assets/synthetic-result.json"
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(m.assess(0,p,digest)["status"],"pass")
        self.assertEqual(m.assess(0,p,"0"*64)["status"],"fail")

    def test_failure_even_with_artifact(self):
        self.assertEqual(m.assess(1,ROOT/"assets/synthetic-result.json")["status"],"fail")

    def test_prerequisite_block_is_distinct(self):
        self.assertEqual(m.assess(127,"missing",blocked_reason="synthetic missing runtime")["status"],"blocked")
