"""Independent checks for axial cleanup in moving projected reference frames."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cleanup_axial import axial_anchors
from cleanup_tracks import build_tracks


LANDMARKS = {11: (105, 124, 99), 12: (55, 124, 99),
             23: (91, 214, 99), 24: (69, 214, 99),
             7: (100, 91, 99), 8: (60, 91, 99)}
REGIONS = {
    "torso": [[80, 165, 1, 0, 26, 43]],
    "chest": [[81, 145, 1, 0, 22, 14]],
    "head": [[80, 90, 1, 0, 24, 18]],
    "left-eye": [[91, 88, 1, 0, 9, 7]],
    "right-eye": [[69, 88, 1, 0, 9, 7]],
    "nose": [[80, 96, 1, 0, 8, 10]],
    "mouth": [[80, 107, 1, 0, 9, 8]],
    "hips": [[80, 215, 1, 0, 25, 19]],
    "left-buttock": [[90, 220, 1, 0, 12, 15]],
}


def fixture(rows, poses=None, shots=None):
    poses = poses or [LANDMARKS] * len(rows)
    manifest = {
        "fps": 30,
        "height": 1280,
        "shots": shots or [[0, len(rows)]],
        "landmarks": list(LANDMARKS),
        "frames": [
            [1280, [[[points[key][0] * 4, points[key][1] * 4, points[key][2]]
                     for key in LANDMARKS]]]
            for points in poses
        ],
    }
    return build_tracks({"frames": rows}, manifest)["frames"]


def moved(index, tilt=.64):
    angle = tilt * math.sin(index * .45)
    cosine, sine = math.cos(angle), math.sin(angle)
    translation = (4 * index, 1.2 * index * index)

    def rotate(x, y):
        return (cosine * x - sine * y, sine * x + cosine * y)

    def point(x, y):
        u, v = rotate(x, y)
        return (u + translation[0], v + translation[1])

    pose = {key: (*point(x, y), confidence) for key, (x, y, confidence) in LANDMARKS.items()}
    row = {key: [[*point(x, y), *rotate(ux, uy), rx, ry] for x, y, ux, uy, rx, ry in fields]
           for key, fields in REGIONS.items()}
    return row, pose


class AxialCleanup(unittest.TestCase):
    def test_torso_head_and_face_keep_time_varying_carrier(self):
        pairs = [moved(index) for index in range(13)]
        rows, poses = map(list, zip(*pairs))
        output = fixture(rows, poses)
        for raw, processed in zip(rows, output):
            for key in REGIONS:
                for expected, actual in zip(raw[key][0], processed[key][0]):
                    self.assertAlmostEqual(expected, actual, delta=.001)

    def test_small_tracking_spike_is_smoothed_relative_to_rotating_torso(self):
        pairs = [moved(index) for index in range(9)]
        rows, poses = map(list, zip(*pairs))
        stable = rows[4]["chest"][0][0]
        rows[4]["chest"][0][0] += 4.0
        cleaned = fixture(rows, poses)
        residual = cleaned[4]["chest"][0][0] - stable
        self.assertGreater(residual, 0)
        self.assertLess(residual, 3.5)
        self.assertEqual(rows[4]["chest"][0][0], stable + 4.0)

    def test_mouth_real_expression_keeps_its_timing(self):
        rows = []
        for i in range(11):
            y = 107 + i * .65 if i < 6 else 116 + (i - 6) * .65
            rows.append(dict(REGIONS, mouth=[[80, y, 1, 0, 9, 8]]))
        cleaned = fixture(rows)
        self.assertAlmostEqual(cleaned[3]["mouth"][0][1], rows[3]["mouth"][0][1], delta=.001)
        self.assertAlmostEqual(cleaned[6]["mouth"][0][1], rows[6]["mouth"][0][1], delta=.001)

    def test_visibility_and_shot_boundaries_stop_cleanup(self):
        face_hidden = {key: value for key, value in REGIONS.items() if key != "mouth"}
        before_gap = dict(REGIONS, mouth=[[83, 107, 1, 0, 9, 8]])
        after_gap = dict(REGIONS, mouth=[[77, 107, 1, 0, 9, 8]])
        rows = [REGIONS, before_gap, face_hidden, after_gap, REGIONS]
        result = fixture(rows)
        self.assertNotIn("mouth", result[2])
        self.assertEqual(result[1]["mouth"], before_gap["mouth"])
        self.assertEqual(result[3]["mouth"], after_gap["mouth"])
        rows = [REGIONS, before_gap, after_gap, REGIONS]
        result = fixture(rows, shots=[[0, 2], [2, 4]])
        self.assertEqual(result, rows)

    def test_front_to_rear_turn_does_not_invent_edited_surfaces(self):
        front = {key: value for key, value in REGIONS.items() if key not in ("hips", "left-buttock")}
        rear = {key: value for key, value in REGIONS.items() if key not in (
            "chest", "left-eye", "right-eye", "nose", "mouth"
        )}
        front_last = dict(front, chest=[[83, 145, 1, 0, 22, 14]])
        rear_first = dict(rear, **{"left-buttock": [[88, 220, -1, 0, 12, 15]]})
        reverse_pose = dict(LANDMARKS)
        for left, right in ((7, 8), (11, 12), (23, 24)):
            reverse_pose[left], reverse_pose[right] = reverse_pose[right], reverse_pose[left]
        rows = [front, front, front_last, rear_first, rear, rear]
        processed = fixture(rows, [LANDMARKS] * 3 + [reverse_pose] * 3)
        self.assertEqual(processed[2]["chest"], front_last["chest"])
        self.assertNotIn("left-buttock", processed[2])
        self.assertEqual(processed[3]["left-buttock"], rear_first["left-buttock"])
        self.assertNotIn("chest", processed[3])
        self.assertNotIn("mouth", processed[3])

    def test_missing_observed_pair_suppresses_its_axial_anchor(self):
        low_shoulder = dict(LANDMARKS)
        low_shoulder[11] = (105, 124, 5)
        partial_face = dict(REGIONS, **{"left-eye": [None]})
        anchors = axial_anchors(low_shoulder, partial_face)
        self.assertEqual(anchors["chest"], [None])
        self.assertEqual(anchors["torso"], [None])
        self.assertEqual(anchors["mouth"], [None])
        self.assertIsNotNone(anchors["head"][0])
        self.assertIsNotNone(anchors["hips"][0])


if __name__ == "__main__":
    unittest.main()
