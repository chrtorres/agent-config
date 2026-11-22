"""Soft-tissue dynamics of added volume, and parity with the browser module."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from soft_body import added_share, soft_body_track, with_offsets

ROOT = Path(__file__).resolve().parents[1]


def walk(stop=12, frames=60):
    """A chest that moves right at constant speed, then stops abruptly."""
    rows = []
    for index in range(frames):
        x = 100+6*min(index, stop)
        rows.append({"chest": [[x, 120, 1, 0, 40, 30]], "head": [[x, 60, 1, 0, 20, 24]]})
    return rows, {"fps": 30, "shots": [[0, frames]]}


class SoftBody(unittest.TestCase):
    def test_added_volume_lags_then_rebounds_after_a_stop(self):
        frames, manifest = walk()
        track = soft_body_track(frames, "chest", (.4, .4), manifest)
        lag = [offset[0][0] for offset in track]
        self.assertEqual(lag[0], 0)
        # Starting to move right, the added mass trails to the left. After
        # the stop it carries on past the anchor, swings back, and settles.
        self.assertLess(min(lag[1:6]), -.1)
        self.assertGreater(max(lag[12:18]), .1)
        self.assertLess(min(lag[17:26]), -.1)
        self.assertLess(abs(lag[-1]), .05*max(abs(value) for value in lag))
        for offset in track:
            self.assertLessEqual(abs(offset[0][0]), .15*30)

    def test_rigid_parts_and_shrinking_edits_have_no_added_motion(self):
        frames, manifest = walk()
        self.assertIsNone(soft_body_track(frames, "head", (.4, .4), manifest))
        self.assertIsNone(soft_body_track(frames, "chest", (-.3, -.2), manifest))
        self.assertEqual(added_share((0, 0)), 0)

    def test_untracked_frames_and_cuts_restart_the_spring(self):
        frames, manifest = walk()
        frames[20] = {}
        manifest["shots"] = [[0, 8], [8, 60]]
        track = soft_body_track(frames, "chest", (.6, .2), manifest)
        self.assertEqual(track[8][0], (0, 0))
        self.assertIsNone(track[20][0])
        self.assertEqual(track[21][0], (0, 0))

    def test_offsets_extend_only_tracked_shapes(self):
        shapes = [[1, 2, 1, 0, 3, 4], None]
        self.assertEqual(with_offsets(shapes, [(.5, -.5), None]), [(1, 2, 1, 0, 3, 4, .5, -.5), None])

    @unittest.skipUnless(shutil.which("node"), "node is required for browser parity")
    def test_browser_simulation_matches_export(self):
        frames, manifest = walk()
        frames[25] = {}
        manifest["frameTimes"] = [index/30+(.004 if index % 3 == 0 else 0) for index in range(60)]
        script = ("import {softBodyTrack} from './app/soft-body.mjs';"
                  "const [frames,manifest]=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(softBodyTrack(frames,'chest',[.5,.3],"
                  "{times:manifest.frameTimes,fps:manifest.fps,shots:manifest.shots})));")
        output = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps([frames, manifest])],
                                cwd=ROOT, check=True, capture_output=True, text=True).stdout
        browser = json.loads(output)
        export = soft_body_track(frames, "chest", (.5, .3), manifest)
        for left, right in zip(browser, export):
            if right[0] is None:
                self.assertIsNone(left[0])
                continue
            for a, b in zip(left[0], right[0]):
                self.assertAlmostEqual(a, b, places=9)


if __name__ == "__main__":
    unittest.main()


class KernelParity(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is required for browser parity")
    def test_browser_shape_kernel_matches_export(self):
        import numpy as np
        from cleanup import displacement
        shapes = {"chest": [[60, 50, .8, .6, 18, 25, 1.5, -.5]], "left-arm": [[20, 30, 0, 1, 8, 20], [28, 60, 1, 0, 9, 18]]}
        amounts = {"chest": [.9, .2], "left-arm": [-.4, .35]}
        points = [[x, y] for x in range(0, 120, 7) for y in range(0, 100, 9)]
        script = ("import {deformation} from './app/regions.mjs';"
                  "const [shapes,amounts,points]=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(points.map(([x,y])=>deformation(x,y,shapes,amounts))));")
        output = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps([shapes, amounts, points])],
                                cwd=ROOT, check=True, capture_output=True, text=True).stdout
        browser = np.array(json.loads(output))
        fields = [(shape, amount) for key, amount in ((key, tuple(value)) for key, value in amounts.items())
                  for shape in shapes[key]]
        x, y = np.array(points, dtype=np.float64).T
        dx, dy = displacement(x, y, fields)
        np.testing.assert_allclose(browser[:, 0], x+dx, atol=1e-9)
        np.testing.assert_allclose(browser[:, 1], y+dy, atol=1e-9)
