import importlib.util
from pathlib import Path
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("creator", SKILL / "scripts/create_app.py")
creator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creator)


class CreationTests(unittest.TestCase):
    def test_complete_copy_imports_without_original_task(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "isolated-app"
            creator.create(destination)
            for relative in ["web/app.mjs", "tests/browser-check.mjs", "objects/formats.json", ".gitignore"]:
                self.assertTrue((destination / relative).is_file())
            self.assertFalse((destination / "evidence").exists())
            result = subprocess.run([sys.executable, "-B", "-c", "import monitor, server; assert len(monitor.PROFILES)==5"], cwd=destination, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_existing_work_and_shared_skill_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            marker = destination / "work.txt"
            marker.write_text("existing work")
            with self.assertRaises(ValueError):
                creator.create(destination)
            self.assertEqual(marker.read_text(), "existing work")
        with self.assertRaises(ValueError):
            creator.create(SKILL / "generated-app")

    def test_symlink_destination_cannot_enter_shared_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            link = Path(folder) / "shared-alias"
            link.symlink_to(SKILL, target_is_directory=True)
            with self.assertRaises(ValueError):
                creator.create(link / "generated-app")


if __name__ == "__main__":
    unittest.main()
