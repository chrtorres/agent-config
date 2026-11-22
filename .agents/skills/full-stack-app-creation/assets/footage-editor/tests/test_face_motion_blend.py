import unittest

import numpy as np

from tools.face_motion_blend import FaceBlend, soften_color_seam


class FaceMotionBlendTests(unittest.TestCase):
    def setUp(self):
        self.crop = np.full((48, 48, 3), 130, np.uint8)
        self.labels = np.ones((48, 48), np.uint8)
        self.inner = np.zeros((48, 48), np.float32)
        self.inner[8:40,8:40] = .6

    def test_stable_boundary_fuses_without_expanding_the_mask(self):
        blend = FaceBlend()
        prior = np.roll(self.inner, 4, axis=1)
        blend.refine(self.crop, self.labels, prior, 0, False)
        refined, _ = blend.refine(self.crop, self.labels, self.inner, .01, False)
        self.assertTrue(np.all(refined <= self.inner))
        self.assertLess(refined[20,10], self.inner[20,10])

    def test_fast_motion_discards_prior_boundary(self):
        blend = FaceBlend()
        blend.refine(self.crop, self.labels, np.roll(self.inner, 4, axis=1), 0, False)
        current, _ = blend.refine(self.crop, self.labels, self.inner, .2, False)
        np.testing.assert_array_equal(current, self.inner)
        self.assertEqual(blend.rapid, 1)

    def test_eyes_come_from_current_frame_instead_of_mask_history(self):
        blend = FaceBlend()
        labels = self.labels.copy()
        labels[18:21,13:17] = 4
        blend.refine(self.crop, labels, self.inner, 0, False)
        labels[18:21,13:17] = 1
        labels[18:21,28:32] = 4
        refined, eyes = blend.refine(self.crop, labels, self.inner, 0, False)
        self.assertFalse(eyes[19,15])
        self.assertTrue(eyes[19,30])
        self.assertEqual(refined[19,30], 0)
        self.assertAlmostEqual(refined[19,15], .6)

    def test_edge_color_moves_toward_target_without_recoloring_core(self):
        target = np.full((48,48,3), 150, np.uint8)
        generated = np.full((48,48,3), 110, np.float32)
        alpha = self.inner.copy()
        alpha[14:34,14:34] = 1
        matched = soften_color_seam(target, generated, alpha)
        self.assertGreater(matched[10,10,0], 110)
        np.testing.assert_array_equal(matched[20,20], generated[20,20])
