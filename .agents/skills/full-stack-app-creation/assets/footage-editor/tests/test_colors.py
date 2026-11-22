"""Hair and facial-feature dyes keep shading and stay inside their masks."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from colors import LUMA, apply_colors, dye, feature_masks, hex_color, valid_colors  # noqa: E402

SQUARE = lambda x, y, r: [[x-r, y-r], [x+r, y-r], [x+r, y+r], [x-r, y+r]]
AREAS = {"lips": SQUARE(50, 70, 12), "mouth": SQUARE(50, 70, 4),
         "eyes": [SQUARE(30, 30, 6), SQUARE(70, 30, 6)], "irises": [[30, 30, 3], [70, 30, 3]],
         "brows": [SQUARE(30, 18, 3), SQUARE(70, 18, 3)]}


class Colors(unittest.TestCase):
    def test_dye_takes_hue_and_keeps_most_shading(self):
        rng = np.random.default_rng(0)
        hair = (rng.uniform(.05, .3, (20, 20, 1))*np.float32([1, .8, .6])).astype(np.float32)
        red = hex_color("#c0301c")
        dyed = dye(hair, red, 1., np.ones((20, 20), np.float32))
        lum_before, lum_after = hair @ LUMA, dyed @ LUMA
        self.assertGreater(np.corrcoef(lum_before.ravel(), lum_after.ravel())[0, 1], .98)
        self.assertTrue(np.all(dyed[..., 0] >= dyed[..., 1]))

    def test_zero_mask_or_strength_changes_nothing(self):
        image = np.random.default_rng(1).uniform(0, 1, (8, 8, 3)).astype(np.float32)
        np.testing.assert_array_equal(dye(image, hex_color("#00ff00"), 1., np.zeros((8, 8), np.float32)), image)
        np.testing.assert_array_equal(dye(image, hex_color("#00ff00"), 0., np.ones((8, 8), np.float32)), image)

    def test_masks_exclude_mouth_opening_and_eyelids(self):
        lips, irises, brows = feature_masks(AREAS, (100, 100))
        self.assertGreater(lips[70, 40], .9)
        self.assertLess(lips[70, 50], .05)
        self.assertGreater(irises[30, 30], .9)
        self.assertLess(irises[30, 36], .05)
        self.assertGreater(brows[18, 30], .5)

    def test_apply_colors_only_touches_dyed_features(self):
        rgb = np.full((100, 100, 3), 150, np.uint8)
        out = apply_colors(rgb, valid_colors({"lips": ["#aa0044", 80]}), None, AREAS)
        np.testing.assert_array_equal(out[5:12], rgb[5:12])
        self.assertFalse(np.array_equal(out[70, 40], rgb[70, 40]))
        np.testing.assert_array_equal(out[30, 30], rgb[30, 30])

    def test_recipe_validation(self):
        self.assertEqual(valid_colors({"hair": ["#123456", 0]}), {})
        with self.assertRaises(ValueError):
            valid_colors({"skin": ["#123456", 20]})
        with self.assertRaises(ValueError):
            valid_colors({"hair": ["red", 20]})


if __name__ == "__main__":
    unittest.main()
