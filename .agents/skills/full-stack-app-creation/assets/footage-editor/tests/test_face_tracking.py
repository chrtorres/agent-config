"""Model-free checks of action tracking, smoothing, blur matching and detail."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from face_swap_video import match_motion_blur, motion_kernel, restore_detail  # noqa: E402
from face_tracking import OneEuro, face_from_points, flow_prediction, ocular, shot_change, histogram, smooth_track  # noqa: E402

FIVE = np.array([[100, 100], [140, 100], [120, 125], [104, 145], [136, 145]], np.float64)


def record(points, cut=False):
    return {"points": None if points is None else np.asarray(points, np.float64), "source": "detect", "cut": cut}


class Smoothing(unittest.TestCase):
    def test_zero_lag_on_steady_motion(self):
        track = [record(FIVE+[6*index, 0]) for index in range(30)]
        smoothed = smooth_track(track, 30)
        for index in range(3, 27):
            np.testing.assert_allclose(smoothed[index][0], track[index]["points"], atol=.35)

    def test_jitter_is_reduced_on_a_still_face(self):
        rng = np.random.default_rng(3)
        noisy = [record(FIVE+rng.normal(0, 1.2, (5, 2))) for _ in range(40)]
        smoothed = np.stack([points for points, _ in smooth_track(noisy, 30)])
        raw = np.stack([item["points"] for item in noisy])
        # Frame-to-frame shake (second difference) is what makes a swap wobble.
        self.assertLess(np.abs(np.diff(smoothed, 2, axis=0)).mean(), .6*np.abs(np.diff(raw, 2, axis=0)).mean())
        self.assertLess(np.abs(smoothed-FIVE).mean(), .8*np.abs(raw-FIVE).mean())

    def test_fast_gap_is_not_guessed(self):
        track = [record(FIVE+[25*index, 0]) for index in range(12)]
        track[5] = track[6] = record(None)
        smoothed = smooth_track(track, 30)
        self.assertIsNone(smoothed[5][0])

    def test_short_gaps_are_bridged_but_not_across_cuts(self):
        track = [record(FIVE+[2*index, 0]) for index in range(20)]
        for index in (5, 6, 7):
            track[index] = record(None)
        track[14] = record(None)
        track[15] = record(FIVE+[30, 0], cut=True)
        smoothed = smooth_track(track, 30)
        self.assertTrue(all(smoothed[index][1] for index in (5, 6, 7)))
        np.testing.assert_allclose(smoothed[6][0], FIVE+[12, 0], atol=.5)
        self.assertIsNone(smoothed[14][0])

    def test_one_euro_follows_a_jump_quickly(self):
        values = np.array([[0.]]*10+[[40.]]*10)
        out = OneEuro(30).run(values, np.array([0.]*9+[15.]*3+[0.]*8))
        self.assertGreater(out[12, 0], 30)


class Flow(unittest.TestCase):
    def test_prediction_follows_moving_texture(self):
        rng = np.random.default_rng(0)
        texture = cv2.GaussianBlur(rng.integers(0, 255, (240, 320)).astype(np.uint8), (0, 0), 1.5)
        moved = np.roll(texture, (4, 9), axis=(0, 1))
        anchors = np.array([[x, y] for x in range(90, 160, 9) for y in range(80, 160, 9)], np.float32)
        predicted, support = flow_prediction(texture, moved, anchors, FIVE)
        self.assertGreater(support, .8)
        np.testing.assert_allclose(predicted, FIVE+[9, 4], atol=.3)

    def test_whip_pan_is_not_a_shot_change(self):
        rng = np.random.default_rng(1)
        frame = cv2.GaussianBlur(rng.integers(0, 255, (180, 320, 3)).astype(np.uint8), (0, 0), 3)
        panned = cv2.blur(np.roll(frame, 60, axis=1), (25, 1))
        other = np.zeros_like(frame)
        other[...] = (200, 40, 10)
        other = cv2.add(other, (frame//6))
        self.assertFalse(shot_change(histogram(frame), histogram(panned)))
        self.assertTrue(shot_change(histogram(frame), histogram(other)))

    def test_detector_row_from_points(self):
        face = face_from_points(FIVE)
        np.testing.assert_allclose(face[4:14], FIVE.reshape(-1))
        self.assertAlmostEqual(float(face[2]), 2.6*ocular(FIVE), places=4)


class Compositing(unittest.TestCase):
    def test_sharp_swap_takes_the_recorded_motion_blur(self):
        rng = np.random.default_rng(2)
        sharp = cv2.GaussianBlur(rng.integers(0, 255, (80, 80, 3)).astype(np.float32), (0, 0), .8)
        recorded = cv2.filter2D(sharp, -1, motion_kernel(np.array([1., 0.]), 9))
        mask = np.ones((80, 80), bool)
        _, length = match_motion_blur(recorded, sharp, mask, np.array([18., 0.]))
        self.assertAlmostEqual(length, 9)
        unchanged, still = match_motion_blur(sharp, sharp, mask, np.array([18., 0.]))
        self.assertEqual(still, 0)
        np.testing.assert_array_equal(unchanged, sharp)

    def test_detail_is_restored_only_on_skin_when_enlarged(self):
        rng = np.random.default_rng(4)
        target = rng.integers(60, 200, (40, 40, 3)).astype(np.uint8)
        overlay = np.full((40, 40, 3), 128, np.float32)
        skin = np.zeros((40, 40), np.float32)
        skin[:, 20:] = 1
        restored = restore_detail(target, overlay, skin, 3.)
        np.testing.assert_array_equal(restored[:, :20], overlay[:, :20])
        self.assertGreater(restored[:, 22:].std(), 5)
        np.testing.assert_array_equal(restore_detail(target, overlay, skin, 1.), overlay)


if __name__ == "__main__":
    unittest.main()
