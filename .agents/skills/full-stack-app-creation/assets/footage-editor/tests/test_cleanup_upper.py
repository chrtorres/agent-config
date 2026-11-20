"""Regression tests for cleanup on observed arms, palms and articulated digits."""
from math import cos, sin
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cleanup_tracks import build_tracks
from cleanup_upper import upper_anchors


def transform(x, y, angle, origin):
    return (
        origin[0] + x * cos(angle) - y * sin(angle),
        origin[1] + x * sin(angle) + y * cos(angle),
    )


def ellipse(x, y, angle, origin, tilt=0, radii=(9, 12)):
    cx, cy = transform(x, y, angle, origin)
    return [cx, cy, cos(angle + tilt), sin(angle + tilt), *radii]


def tracks(count, frame_at):
    frames = [frame_at(i) for i in range(count)]
    return build_tracks(
        {"frames": [regions for _, regions in frames]},
        {
            "fps": 30,
            "height": 720,
            "landmarks": [11, 13, 15],
            "shots": [[0, count]],
            "frames": [
                [720, [[[x * 4, y * 4, 99] for x, y in points]]]
                for points, _ in frames
            ],
        },
    )["frames"]


class UpperLimbCleanupTests(unittest.TestCase):
    def test_independent_arm_slots_share_the_recorded_elbow(self):
        points = {11: (20, 40, 99), 13: (56, 44, 99), 15: (63, 78, 99)}
        regions = {"left-arm": [[32, 42, 0, 1, 11, 23], [60, 64, 1, 0, 9, 19]]}
        arm = upper_anchors(points, regions)["left-arm"]
        self.assertEqual(arm, [[20, 40, 56, 44], [56, 44, 63, 78]])
        points[15] = (63, 78, 10)
        self.assertEqual(upper_anchors(points, regions)["left-arm"], [arm[0], None])

    def test_rotating_forearm_ignores_local_jitter_without_lagging_motion(self):
        def frame(i):
            angle, origin = .16 * i, (180 + 13 * i, 190 - 8 * i)
            points = [transform(x, 0, angle, origin) for x in (0, 40, 90)]
            jitter = 1.25 if i == 3 else 0
            upper = ellipse(20, 0, angle, origin, 1.57, (15, 28))
            forearm = ellipse(66, jitter, angle, origin, 1.57, (15, 28))
            return points, {"left-arm": [upper, forearm]}

        result = tracks(7, frame)
        for i, row in enumerate(result):
            with self.subTest(frame=i):
                expected = transform(66, 0, .16 * i, (180 + 13 * i, 190 - 8 * i))
                actual = row["left-arm"][1]
                # No averaging of the carrier in screen space, even when it
                # translates 13 pixels and rotates .16 radians per frame.
                self.assertLess(abs(actual[0] - expected[0]), .75)
                self.assertLess(abs(actual[1] - expected[1]), .75)
                self.assertAlmostEqual(actual[2], cos(.16 * i + 1.57), places=3)
                self.assertAlmostEqual(actual[3], sin(.16 * i + 1.57), places=3)

    def test_finger_flex_and_occlusion_do_not_copy_neighboring_frames(self):
        def frame(i):
            origin = (260 + 8 * i, 210 + 5 * i)
            angle = .11 * i
            points = [transform(x, 0, angle, origin) for x in (0, 45, 90)]
            palm = ellipse(105, 0, angle, origin, 1.57, (13, 19))
            # A large bend at frame 4 is genuine movement of the digit
            # relative to the palm. Frame 6 has no tracked finger at all.
            finger = ellipse(124, 14 if i == 4 else 0, angle, origin,
                             2.47 if i == 4 else 1.57, (4, 11))
            return points, {"left-hand": [palm], "left-index-finger": [None if i == 6 else finger]}

        result = tracks(9, frame)
        for i in (4, 5, 6, 7):
            self.assertEqual(result[i]["left-index-finger"], frame(i)[1]["left-index-finger"])
        self.assertEqual(result[6]["left-index-finger"], [None])


if __name__ == "__main__":
    unittest.main()
