from pathlib import Path
import tempfile
import unittest

from scripts.run_checks import source_hashes


class ManifestScopeTests(unittest.TestCase):
    def test_authored_sources_exclude_dependency_and_evidence_readmes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ["README.md", "web/app.mjs", "objects/formats.json", "node_modules/vendor/README.md", "evidence/README.md", "web/node_modules/vendor/code.mjs", "scripts/__pycache__/module.pyc"]:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("synthetic fixture")
            result = source_hashes(root)
            self.assertEqual(set(result), {"README.md", "web/app.mjs", "objects/formats.json"})
            self.assertTrue(all(len(digest) == 64 for digest in result.values()))


if __name__ == "__main__":
    unittest.main()
