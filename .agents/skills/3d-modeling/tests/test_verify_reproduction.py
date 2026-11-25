"""Behavioural test for verify_reproduction.py using a synthetic project whose 'entrypoint'
writes a marker, an artifact and a metrics file. No Blender, no project data.
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(os.path.dirname(HERE), 'scripts', 'verify_reproduction.py')


class VerifyReproductionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='repro-')
        # a fake build entrypoint: writes artifact, metrics, and a done marker
        self.build = os.path.join(self.root, 'build.py')
        open(self.build, 'w').write(textwrap.dedent("""
            import json, os, sys
            root = os.path.dirname(os.path.abspath(__file__))
            open(os.path.join(root, 'model.glb'), 'wb').write(b'x' * 5000)
            json.dump({"scores": {"iou": float(sys.argv[1])}}, open(os.path.join(root, 'scores.json'), 'w'))
            open(os.path.join(root, 'build.done'), 'w').write('rc=0 seconds=0')
        """))
        self.man = os.path.join(self.root, 'reproduce.json')

    def _write_manifest(self, iou_arg, min_iou=0.99):
        json.dump({
            "project": "synthetic", "approved_version": "v1",
            "entrypoint": {"cmd": [sys.executable, "build.py", str(iou_arg)], "cwd": ".",
                           "timeout_s": 30, "done_marker": "build.done", "marker_ok_regex": "rc=0"},
            "artifacts": [{"path": "model.glb", "min_bytes": 1000}],
            "metrics": {"source": "scores.json", "checks": [{"pointer": "scores.iou", "min": min_iou}]},
        }, open(self.man, 'w'))

    def _run(self, *extra):
        return subprocess.run([sys.executable, VERIFY, self.man, *extra], capture_output=True, text=True)

    def test_reproduces_and_passes(self):
        self._write_manifest(0.995)
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('OK', r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.root, 'model.glb')))

    def test_metric_below_bar_fails(self):
        self._write_manifest(0.80)                 # entrypoint runs, but score misses the bar
        r = self._run()
        self.assertEqual(r.returncode, 1)
        self.assertIn('FAILED', r.stdout)
        self.assertIn('metric scores.iou', r.stdout)

    def test_dry_run_checks_disk_without_building(self):
        self._write_manifest(0.995)
        self._run()                                # produce artifacts once
        os.remove(os.path.join(self.root, 'build.done'))
        r = self._run('--dry-run')                 # must pass on existing artifacts, no rebuild
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('skipped (--dry-run)', r.stdout)


if __name__ == '__main__':
    unittest.main()
