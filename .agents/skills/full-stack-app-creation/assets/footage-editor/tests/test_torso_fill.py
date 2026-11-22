"""Check that an exposed torso edge is reconstructed from source pixels."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_edit import bounded_remap


class TorsoFill(unittest.TestCase):
    def test_same_frame_donor_replaces_exposed_silhouette(self):
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        rgb[:, :, 0] = np.arange(100, dtype=np.uint8)
        rgb[:, :, 1] = 160
        rgb[:, 30:70] = [200, 65, 20]
        matte = np.zeros((100, 100), dtype=np.float32)
        matte[:, 30:70] = 1
        fields = [([50, 50, 1, 0, 34, 36], [-.51, .54])]

        result = bounded_remap(rgb.copy(), matte, fields)

        np.testing.assert_array_equal(result[50, 50], rgb[50, 50])
        # The narrower torso exposes background, filled from nearby
        # background rather than from the old body edge.
        self.assertEqual(int(result[50, 31, 1]), 160)
        self.assertIn(int(result[50, 31, 0]), range(8, 30))
        self.assertTrue(np.all(result[:, 31:34, 1] == 160))


if __name__ == "__main__":
    unittest.main()
