"""Synthetic checks for volatile storage."""
import os
from pathlib import Path
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
