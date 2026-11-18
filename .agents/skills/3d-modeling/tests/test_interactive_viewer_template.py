import json
import pathlib
import re
import unittest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
VIEWER_DIR = SKILL_DIR / "assets" / "interactive-review-viewer"


class InteractiveViewerTemplateTests(unittest.TestCase):
    def test_template_has_required_files_and_placeholders(self):
        for name in ("index.html", "styles.css", "viewer.js", "metadata.json", "README.md"):
            self.assertTrue((VIEWER_DIR / name).is_file(), name)
        metadata = json.loads((VIEWER_DIR / "metadata.json").read_text())
        self.assertIn("facts", metadata)
        self.assertIn("<version>", metadata["facts"]["Version"])

    def test_viewer_uses_portable_glb_and_review_controls(self):
        html = (VIEWER_DIR / "index.html").read_text()
        js = (VIEWER_DIR / "viewer.js").read_text()
        self.assertIn('src="viewer.js"', html)
        self.assertIn('"three"', html)
        for expected in ("model.glb", "metadata.json", "OrbitControls", "GLTFLoader", "wireframe", "autoRotate"):
            self.assertIn(expected, js)
        self.assertNotRegex(js, re.compile(r"/home/|/Users/|[A-Za-z]:\\"))


if __name__ == "__main__":
    unittest.main()
