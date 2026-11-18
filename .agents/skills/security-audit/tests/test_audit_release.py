import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import audit_release


class AuditReleaseTests(unittest.TestCase):
    def test_safe_synthetic_tree_has_no_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "demo.json").write_text(json.dumps({"host": "atlas-demo", "label": "Archive"}))
            self.assertEqual(audit_release.scan_root(root), [])

    def test_tree_reports_private_patterns_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.log").write_text("host=/home/example-user\nuid=abc@example.test\n")
            categories = {item["category"] for item in audit_release.scan_root(root)}
            self.assertEqual(categories, {"home-path", "email"})

    def test_archive_is_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "release.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                payload = b"mount=/media/example-user/Drive\n"
                info = tarfile.TarInfo("release/report.txt")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            findings = audit_release.scan_archive(archive)
            self.assertEqual({item["category"] for item in findings}, {"media-user-path"})

    def test_placeholder_negative_fixture_is_not_a_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test.py").write_text("body = b'password=no'\n")
            self.assertEqual(audit_release.scan_root(root), [])


if __name__ == "__main__":
    unittest.main()
