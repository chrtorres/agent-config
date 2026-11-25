"""Behavioural test for score_appearance.py on a synthetic fixture.

Runs the whole scorer end to end and asserts the observable outcomes a reviewer would check:
a mean class IoU in a sane range, a small known per-class colour difference on the tinted
band, and that colour/edge/grain are reported. No project data; the fixture is generated here.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CLASSES = json.dumps({"walnut": [214, 140, 70], "charA": [96, 60, 40], "charB": [80, 100, 140]})


class ScoreAppearanceTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='appearance-')
        subprocess.run([sys.executable, os.path.join(HERE, 'fixtures', 'make_appearance_fixture.py'),
                        '--out', self.d], check=True, capture_output=True)

    def _score(self, color=True):
        cmd = [sys.executable, os.path.join(SKILL, 'scripts', 'score_appearance.py'),
               '--render-classmap', os.path.join(self.d, 'render_classmap.png'),
               '--ref-classmap', os.path.join(self.d, 'ref_classmap.png'),
               '--classes', CLASSES, '--out', os.path.join(self.d, 'scores.json')]
        if color:
            cmd += ['--render-color', os.path.join(self.d, 'render_color.png'),
                    '--ref-color', os.path.join(self.d, 'ref_color.png')]
        subprocess.run(cmd, check=True, capture_output=True)
        return json.load(open(os.path.join(self.d, 'scores.json')))

    def test_classmap_iou_in_range(self):
        r = self._score(color=False)['classmap_iou']
        # a 4 px shift on a 120 px frame: high but not perfect IoU, all three classes present
        self.assertIn('mean_iou', r)
        self.assertGreater(r['mean_iou'], 0.80)
        self.assertLess(r['mean_iou'], 0.999)
        for k in ('iou_walnut', 'iou_charA', 'iou_charB'):
            self.assertGreater(r[k], 0.5)
        self.assertGreaterEqual(r['dont_care_share'], 0.0)

    def test_colour_difference_detected(self):
        r = self._score(color=True)
        de = r['dE2000']
        self.assertIsNotNone(de['mean_dE2000'])
        # walnut was tinted (+14 on red); charB untouched -> walnut dE clearly larger than charB
        self.assertGreater(de['walnut']['dE2000'], de['charB']['dE2000'])
        self.assertLess(de['charB']['dE2000'], 3.0)

    def test_optional_metrics_reported(self):
        r = self._score(color=True)
        self.assertIn('edge_f', r)
        self.assertIn('grain', r)


if __name__ == '__main__':
    unittest.main()
