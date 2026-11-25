import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CHECKER = SKILL_ROOT / "scripts" / "check_preserved_subassembly.py"


CREATE_SCENE = """
import bpy
import sys
from pathlib import Path

output, changed = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
for index, x in enumerate((-1.5, 1.5), 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0))
    obj = bpy.context.object
    obj.name = f'Approved part {index}'
    obj['source'] = 'approved'
if changed == 'yes':
    bpy.data.objects['Approved part 2'].data.vertices[0].co.x += 0.125
bpy.ops.wm.save_as_mainfile(filepath=str(Path(output).resolve()))
"""


class PreservedSubassemblyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blender = shutil.which("blender")
        if not cls.blender:
            raise unittest.SkipTest("Blender is not installed or not on PATH")

    def create_scene(self, script, output, changed):
        result = subprocess.run(
            [self.blender, "--background", "--python", str(script), "--", str(output), changed],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_check(self, source, candidate):
        return subprocess.run(
            [self.blender, "--background", "--python", str(CHECKER), "--",
             str(source), str(candidate), "--prefix", "Approved part",
             "--candidate-property", "source=approved"],
            capture_output=True, text=True, check=False,
        )

    def test_exact_match_and_changed_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            creator = root / "create_fixture.py"
            creator.write_text(CREATE_SCENE)
            source, exact, changed = (root / name for name in ("source.blend", "exact.blend", "changed.blend"))
            self.create_scene(creator, source, "no")
            self.create_scene(creator, exact, "no")
            self.create_scene(creator, changed, "yes")
            self.assertEqual(self.run_check(source, exact).returncode, 0)
            failure = self.run_check(source, changed)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn('"changed": [', failure.stdout)
            self.assertIn('"Approved part 2"', failure.stdout)


if __name__ == "__main__":
    unittest.main()
