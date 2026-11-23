"""Behavioural tests for the breed/standard anatomy and coat-refinement helpers (synthetic inputs only).

    python3 -m unittest <skill-dir>/tests/test_standard_and_coat_tools.py -v
Requires numpy, scipy, scikit-image and Pillow.
"""
import json, os, subprocess, sys, tempfile, unittest
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); SCRIPTS = os.path.join(os.path.dirname(HERE), 'scripts')
sys.path.insert(0, SCRIPTS)
import sdf_coat_demo, register_exemplar_overlay as reo, sweep_params, photo_measure_grid  # noqa: E402


class CoatDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.rep = {}
        for k in (1.0, 0.85):
            out = os.path.join(cls.tmp, f'k{k}')
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'sdf_coat_demo.py'), '--out', out, '--warp-k', str(k)],
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            cls.rep[k] = json.load(open(os.path.join(out, 'report.json')))

    def test_solids_closed_and_tiled(self):
        for k, rep in self.rep.items():
            for name in ('whole', 'white', 'black'):
                self.assertEqual(rep[name]['boundary_edges'], 0, (k, name))
                self.assertEqual(rep[name]['nonmanifold_edges'], 0, (k, name))
            self.assertEqual(rep['whole']['components'], 1)
            self.assertLess(rep['tiling_error'], 0.01)

    def test_flecks_exist_in_both_colours(self):
        rep = self.rep[0.85]
        self.assertGreater(rep['black']['components'], 10)   # ticking on the white legs
        self.assertGreater(rep['white']['components'], 5)    # frosting inside the black patches

    def test_markings_follow_the_warp(self):
        """The saddle's front edge on the back line sits at warp.fwd(-2) in the new world for any warp."""
        for k in (1.0, 0.85):
            V = read_ply(os.path.join(self.tmp, f'k{k}', 'black.ply'))
            band = V[(np.abs(V[:, 1]) < 0.5) & (V[:, 2] > 15) & (V[:, 0] < 4)]
            expect = sdf_coat_demo.Warp(2.0, k).fwd(-2.0)
            self.assertAlmostEqual(band[:, 0].max(), expect, delta=0.45)

    def test_boundary_guard(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'sdf_coat_demo.py'), '--out', os.path.join(self.tmp, 'clip'),
                            '--hi', '16', '9', '15'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3); self.assertIn('grid boundary', r.stderr)


def read_ply(path):
    with open(path, 'rb') as f:
        n = 0
        while True:
            line = f.readline().decode().strip()
            if line.startswith('element vertex'):
                n = int(line.split()[-1])
            if line == 'end_header':
                break
        return np.frombuffer(f.read(12 * n), '<f4').reshape(n, 3)


class Overlay(unittest.TestCase):
    def test_registration_round_trip(self):
        """A figure drawn from the silhouette itself, at another scale and mirrored, registers to IoU ~ 1."""
        tmp = tempfile.mkdtemp()
        sil = np.zeros((200, 300), np.uint8); sil[60:150, 80:220] = 255   # a 140 x 90 px box, origin_px (150, 150)
        Image.fromarray(sil).save(os.path.join(tmp, 'sil.png'))
        m = dict(px_per_unit=5.0, origin_px=[150, 150], forward='right')
        json.dump(m, open(os.path.join(tmp, 'map.json'), 'w'))
        # model box: x in [-14, 14], z in [0, 18]; landmark (x=0, z=18). Figure: 3 px/unit, faces left, ground at v=100
        fig = np.full((120, 200), 255, np.uint8); mask = np.zeros_like(fig)
        u0 = 100; mask[100 - 54:100, u0 - 42:u0 + 42] = 255
        Image.fromarray(fig).save(os.path.join(tmp, 'fig.png')); Image.fromarray(mask).save(os.path.join(tmp, 'mask.png'))
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'register_exemplar_overlay.py'), '--figure', os.path.join(tmp, 'fig.png'),
                            '--ground-v', '100', '--landmark-uv', str(u0), '46', '--silhouette', os.path.join(tmp, 'sil.png'),
                            '--silhouette-map', os.path.join(tmp, 'map.json'), '--model-landmark-xz', '0', '18',
                            '--figure-faces', 'left', '--figure-mask', os.path.join(tmp, 'mask.png'), '--out', os.path.join(tmp, 'o.png')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertAlmostEqual(res['scale_px_per_unit'], 3.0, places=3)
        self.assertGreater(res['silhouette_iou'], 0.95)


class Sweep(unittest.TestCase):
    def test_grid_ranking_and_fit_label(self):
        tmp = tempfile.mkdtemp(); grid = os.path.join(tmp, 'grid.json')
        json.dump({'a.x': [1, 2, 3], 'a.y': [0, 1]}, open(grid, 'w'))
        scorer = os.path.join(tmp, 'score.py')
        open(scorer, 'w').write("import json,sys\np=json.load(open(sys.argv[1]))['a']\nprint('log line')\n"
                                "print(json.dumps({'s': -(p['x']-2)**2 - p['y']}))\n")
        out = os.path.join(tmp, 'out')
        rc = sweep_params.main(['--grid', grid, '--command', f'{sys.executable} {scorer} {{params}}', '--out', out, '--score', 's'])
        self.assertEqual(rc, 0)
        res = json.load(open(os.path.join(out, 'sweep.json')))
        self.assertEqual(res['best']['params'], {'a.x': 2, 'a.y': 0})
        self.assertEqual(len(res['runs']), 6); self.assertIn('FIT score', res['note'])

    def test_bad_output_fails(self):
        tmp = tempfile.mkdtemp(); grid = os.path.join(tmp, 'g.json'); json.dump({'x': [1]}, open(grid, 'w'))
        rc = sweep_params.main(['--grid', grid, '--command', 'echo not-json', '--out', os.path.join(tmp, 'o'), '--score', 's'])
        self.assertEqual(rc, 2)


class Grid(unittest.TestCase):
    def test_grid_size(self):
        tmp = tempfile.mkdtemp(); p = os.path.join(tmp, 'p.png'); Image.new('RGB', (300, 200), 'gray').save(p)
        im = photo_measure_grid.grid(p, (50, 40, 250, 140), zoom=2.0, step=20)
        self.assertEqual(im.size, (400, 200))


if __name__ == '__main__':
    unittest.main()
