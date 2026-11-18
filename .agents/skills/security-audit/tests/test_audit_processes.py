import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import audit_processes


class AuditProcessTests(unittest.TestCase):
    def test_safe_command_line_has_no_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory) / "101"
            proc.mkdir()
            (proc / "cmdline").write_bytes(b"/usr/bin/demo\0--name\0synthetic\0")
            self.assertEqual(audit_processes.scan_proc(Path(directory)), [])

    def test_credential_value_is_reported_without_value(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory) / "202"
            proc.mkdir()
            (proc / "cmdline").write_bytes(
                b"/opt/demo\0--api-key\0synthetic-secret-value\0--mode\0test\0"
            )
            findings = audit_processes.scan_proc(Path(directory))
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["field"], "api-key")
            self.assertEqual(findings[0]["category"], "process-command-line-credential")
            self.assertNotIn("synthetic-secret-value", str(findings))

    def test_equals_form_is_reported_without_value(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory) / "303"
            proc.mkdir()
            (proc / "cmdline").write_bytes(b"demo\0--password=synthetic\0")
            findings = audit_processes.scan_proc(Path(directory))
            self.assertEqual(findings[0]["field"], "password")
            self.assertNotIn("synthetic", str(findings))


if __name__ == "__main__":
    unittest.main()
