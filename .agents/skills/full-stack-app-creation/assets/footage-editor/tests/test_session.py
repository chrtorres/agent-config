"""Synthetic checks for volatile storage."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from run import session_directory


class SessionPrivacy(unittest.TestCase):
    def test_session_directory_is_private_and_removed_after_success(self):
        with session_directory() as folder:
            self.assertEqual(folder.parent, Path("/dev/shm"))
            self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
            (folder / "synthetic.txt").write_text("synthetic placeholder")
        self.assertFalse(folder.exists())

    def test_session_directory_is_removed_after_failure(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            with session_directory() as folder:
                (folder / "synthetic.txt").write_text("synthetic placeholder")
                raise RuntimeError("synthetic failure")
        self.assertFalse(os.path.lexists(folder))


class LauncherSetup(unittest.TestCase):
    def test_missing_runtime_is_reported_before_starting_http(self):
        app = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as folder:
            isolated = Path(folder)
            shutil.copy(app / "run.py", isolated)
            (isolated / "app").mkdir()
            shutil.copy(app / "app" / "serve.py", isolated / "app")
            result = subprocess.run([sys.executable, "-E", "-S", "-B", "run.py"],
                                    cwd=isolated, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("Install requirements.txt", result.stderr)
