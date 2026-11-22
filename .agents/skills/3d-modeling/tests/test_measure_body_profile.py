"""Silhouette measurement on a synthetic lofted body: edge sampling fills the bands between
widely spaced rings, an excluded subtree is ignored, and the root scale is divided out."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / 'scripts' / 'measure_body_profile.py'
BLENDER = shutil.which('blender')

FIXTURE = r'''
import bpy, sys
from pathlib import Path
out = Path(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True)
root = bpy.data.objects.new('Root', None); bpy.context.scene.collection.objects.link(root)
root.scale = (2, 2, 2)
# A 1 m tall elliptical body with rings only at 0 and 1 m: 0.20 wide, 0.10 back, 0.15 front.
import math
verts, faces, n = [], [], 24
for z in (0.0, 1.0):
    for i in range(n):
        a = math.tau * i / n
        y = (0.10 if math.cos(a) > 0 else 0.15) * math.cos(a)
        verts.append((0.20 * math.sin(a), y, z))
faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
mesh = bpy.data.meshes.new('Body'); mesh.from_pydata(verts, [], faces)
body = bpy.data.objects.new('Body', mesh); bpy.context.scene.collection.objects.link(body); body.parent = root
# An arm far to the side that must be excluded.
bpy.ops.mesh.primitive_cube_add(size=0.1, location=(0.6, 0, 0.5)); arm = bpy.context.object
arm.name = 'Arm'; arm.parent = root
bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB', export_yup=True)
'''


@unittest.skipUnless(BLENDER, 'Blender is not on PATH')
class MeasureBodyProfile(unittest.TestCase):
    def test_rows_cover_bands_between_rings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'fixture.py').write_text(FIXTURE)
            glb = tmp / 'body.glb'
            subprocess.run([BLENDER, '-b', '--python-exit-code', '1', '--python', str(tmp / 'fixture.py'),
                            '--', str(glb)], check=True, capture_output=True)
            result = tmp / 'profile.json'
            subprocess.run([BLENDER, '-b', '--python-exit-code', '1', '--python', str(SCRIPT), '--',
                            str(glb), '--root', 'Root', '--exclude', 'Arm', '--step', '0.1',
                            '--json', str(result)], check=True, capture_output=True)
            data = json.loads(result.read_text())
            heights = [row[0] for row in data['rows']]
            self.assertEqual(data['scale'], 2)
            for mid in (0.3, 0.5, 0.7):
                self.assertIn(mid, heights, 'bands between the rings must be sampled')
            for height, back, side, front in data['rows']:
                self.assertAlmostEqual(side, 0.20, delta=.01, msg='arm excluded, scale divided out')
                self.assertAlmostEqual(back, 0.10, delta=.01)
                self.assertAlmostEqual(front, 0.15, delta=.01)


if __name__ == '__main__':
    unittest.main()
