import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecordTests(unittest.TestCase):
    def run_record(self, text):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record.md"
            record.write_text(text)
            return subprocess.run([sys.executable, str(ROOT / "scripts/check_refinement.py"), str(record)],
                                  capture_output=True, text=True)

    def test_complete_example(self):
        text = (ROOT / "assets/example-refinement.md").read_text()
        self.assertEqual(self.run_record(text).returncode, 0)

    def test_missing_sections(self):
        result = self.run_record("## Outcome\nA valid goal.\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("baseline, decisions, validation, handoff", result.stdout)

    def test_empty_section(self):
        result = self.run_record((ROOT / "assets/example-refinement.md").read_text().split("## Handoff")[0] + "## Handoff\n\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty: handoff", result.stdout)
