import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scripts" / "stage_release.py"


class StageReleaseTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.destination = self.root / "release"
        (self.source / "entry.py").write_text(
            "from logic import transform\nimport sys\nprint(transform(sys.stdin.read()))\n",
            encoding="utf-8",
        )
        (self.source / "logic.py").write_text(
            "def transform(value):\n    return value.strip().upper()\n", encoding="utf-8"
        )
        (self.source / "fixture.log").write_text("synthetic runtime data", encoding="utf-8")
        self.manifest = self.root / "allowlist.json"

    def stage(self, entries):
        self.manifest.write_text(json.dumps(entries), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", HELPER, self.source, self.manifest, self.destination],
            capture_output=True, text=True, check=False,
        )

    def test_build_from_staged_source_with_only_runtime_input(self):
        result = self.stage(["entry.py", "logic.py"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.source.rename(self.root / "unavailable-source")
        self.assertEqual({p.name for p in self.destination.iterdir()}, {"entry.py", "logic.py"})
        run = subprocess.run(
            [sys.executable, "-I", "-B", "-c", "import runpy,sys; sys.path.insert(0,'.'); runpy.run_path('entry.py')"],
            cwd=self.destination, input="synthetic example\n", capture_output=True, text=True, check=True,
        )
        self.assertEqual(run.stdout, "SYNTHETIC EXAMPLE\n")
        self.assertEqual({p.name for p in self.destination.iterdir()}, {"entry.py", "logic.py"})

    def test_keeps_executable_status_without_copying_mtime(self):
        entry = self.source / "entry.py"
        os.utime(entry, (1, 1))
        entry.chmod(0o700)
        self.assertEqual(self.stage(["entry.py"]).returncode, 0)
        staged = (self.destination / "entry.py").stat()
        self.assertTrue(staged.st_mode & 0o111)
        self.assertNotEqual(staged.st_mtime, entry.stat().st_mtime)

    def test_refuses_existing_destination(self):
        self.destination.mkdir()
        keep = self.destination / "keep.txt"
        keep.write_text("synthetic", encoding="utf-8")
        self.assertNotEqual(self.stage(["entry.py"]).returncode, 0)
        self.assertEqual(list(self.destination.iterdir()), [keep])

    def test_rejects_invalid_and_escaping_paths_without_partial_output(self):
        for path in ("../outside.py", str(self.source / "entry.py"), "", r"folder\entry.py", 42):
            with self.subTest(path=path):
                self.assertNotEqual(self.stage(["entry.py", path]).returncode, 0)
                self.assertFalse(self.destination.exists())

    def test_rejects_symlinks_in_source_paths(self):
        (self.source / "linked.py").symlink_to(self.source / "entry.py")
        (self.source / "linked-dir").symlink_to(self.source, target_is_directory=True)
        for path in ("linked.py", "linked-dir/entry.py"):
            self.assertNotEqual(self.stage([path]).returncode, 0)
            self.assertFalse(self.destination.exists())

    def test_rejects_directory_and_missing_file(self):
        (self.source / "nested").mkdir()
        for path in ("nested", "missing.py"):
            self.assertNotEqual(self.stage([path]).returncode, 0)
            self.assertFalse(self.destination.exists())

    def test_refuses_destination_inside_source(self):
        self.destination = self.source / "release"
        self.assertNotEqual(self.stage(["entry.py"]).returncode, 0)
        self.assertFalse(self.destination.exists())
