import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('storage_creator', SKILL/'scripts/create_storage_app.py')
creator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creator)


class StorageCreationTests(unittest.TestCase):
    def test_copy_is_complete_and_imports_without_task(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)/'app'
            creator.create(dest)
            for file in ['jit.py', 'telemetry.py', 'tests/test_jit.py', 'tests/browser.mjs', 'package-lock.json', 'reference/storage-sweep.sh']:
                self.assertTrue((dest/file).is_file())
            self.assertFalse((dest/'evidence').exists())
            self.assertFalse((dest/'.runtime').exists())
            result = subprocess.run([sys.executable, '-B', '-c', 'import server,jit,telemetry; assert telemetry.demo_snapshot()["source"]=="demo"'], cwd=dest, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_conflicts_and_skill_alias_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                creator.create(root)
            alias = root/'shared'
            alias.symlink_to(SKILL, target_is_directory=True)
            with self.assertRaises(ValueError):
                creator.create(alias/'new-app')
        with self.assertRaises(ValueError):
            creator.create(SKILL/'new-app')
