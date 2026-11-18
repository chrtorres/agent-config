import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = SKILL_ROOT / "scripts" / "create_box_frame.py"
RENDERER = SKILL_ROOT / "scripts" / "render_preview.py"


class BoxFrameWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blender = shutil.which("blender")
        if not cls.blender:
            raise unittest.SkipTest("Blender is not installed or not on PATH")

    def test_generate_and_render_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "exports"
            preview = root / "preview.png"
            create = subprocess.run(
                [self.blender, "--background", "--python", str(GENERATOR), "--", "--output-dir", str(output)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            self.assertTrue((output / "box-frame.blend").is_file())
            inspect = subprocess.run(
                [self.blender, "--background", str(output / "box-frame.blend"), "--python-expr",
                 "import bpy; o=bpy.data.objects['Box_Frame']; assert all(abs(v-5.0)<1e-4 for v in o.dimensions); assert o['beam_count']==12"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            render = subprocess.run(
                [self.blender, "--background", "--python", str(RENDERER), "--", "--blend", str(output / "box-frame.blend"), "--output", str(preview)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            self.assertTrue(preview.is_file())
            self.assertGreater(preview.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
