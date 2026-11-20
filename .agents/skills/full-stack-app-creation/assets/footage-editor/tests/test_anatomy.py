"""Check detailed projected supports and their fallback hierarchy."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from anatomy import catalog, detail_anchors, facial_details, hand_details, pose_details
from cleanup_tracks import build_tracks


POSE = {
    0: (150, 77, 99), 7: (169, 83, 99), 8: (128, 84, 99),
    11: (200, 120, 99), 12: (100, 120, 99), 13: (225, 166, 99), 14: (76, 169, 99),
    15: (246, 220, 99), 16: (61, 224, 99), 23: (180, 254, 99), 24: (120, 254, 99),
    25: (182, 363, 99), 26: (115, 364, 99), 27: (189, 476, 99), 28: (114, 479, 99),
    29: (188, 481, 99), 30: (111, 481, 99), 31: (213, 486, 99), 32: (85, 485, 99),
}
FINGERS = {"index-finger": ("index finger", (5, 6, 7, 8))}


class AnatomyDetails(unittest.TestCase):
    def test_detected_front_and_rear_trunk_are_separate(self):
        front = pose_details(POSE, lambda point: True)
        self.assertIn("abdomen", front)
        self.assertNotIn("upper-back", front)
        rear = {key: (300-x, y, confidence) for key, (x, y, confidence) in POSE.items()}
        self.assertIn("upper-back", pose_details(rear, lambda point: True))
        self.assertNotIn("abdomen", pose_details(rear, lambda point: True))
        self.assertIn("left-forearm", front)
        self.assertIn("left-toe-area", front)

    def test_new_pose_support_respects_matte_and_landmark_confidence(self):
        self.assertEqual({}, pose_details(POSE, lambda point: False))
        points = POSE | {15: (246, 220, 22), 29: (188, 481, 24)}
        result = pose_details(points, lambda point: 0 < point[0] < 220)
        self.assertIn("right-elbow", result)
        self.assertNotIn("left-elbow", result)
        self.assertNotIn("left-forearm", result)
        self.assertNotIn("left-heel", result)
        self.assertTrue(all(0 < shape[0] < 220 and math.isclose(math.hypot(*shape[2:4]), 1, abs_tol=.001)
                        for shapes in result.values() for shape in shapes))

    def test_facial_landmarks_place_precise_visible_supports(self):
        pixels = [(50, 50)] * 468
        for index, x in ((33, 30), (133, 49), (362, 51), (263, 70)):
            pixels[index] = (x, 43)
        for index, y in ((0, 58), (13, 59), (37, 57), (267, 57),
                         (14, 65), (17, 66), (84, 64), (314, 64)):
            pixels[index] = (50, y)
        visible = facial_details(pixels, (1, 0, 40), lambda point: point[1] < 62)
        self.assertIn("forehead", visible)
        self.assertIn("left-upper-eyelid", visible)
        self.assertIn("upper-lip", visible)
        self.assertNotIn("lower-lip", visible)

    def test_hand_subparts_are_nested_and_keep_foreground_constraint(self):
        hand = [(35, 90)] * 21
        for index, y in ((9, 70), (5, 64), (6, 56), (7, 49), (8, 43)):
            hand[index] = (35, y)
        result = hand_details("left", hand, FINGERS, 25, lambda point: point[1] > 47)
        self.assertIn("left-palm", result)
        self.assertIn("left-index-finger-base", result)
        self.assertNotIn("left-index-finger-tip", result)
        available = catalog(("left",), FINGERS)
        self.assertEqual("left-index-finger", available["left-index-finger-tip"][1])
        self.assertEqual("left-eye", available["left-upper-eyelid"][1])

    def test_cleanup_uses_correct_local_carriers_and_preserves_gaps(self):
        supports = pose_details(POSE, lambda point: True)
        parent = {"left-forearm": "left-arm", "left-foot": "left-leg"}
        items = {key: supports[key] for key in parent}
        frames = [items, {"left-forearm": supports["left-forearm"]}, items]
        anchors = detail_anchors(POSE, items, parent, {})
        self.assertEqual([*POSE[13][:2], *POSE[15][:2]], anchors["left-forearm"][0])
        self.assertEqual([*POSE[29][:2], *POSE[31][:2]], anchors["left-foot"][0])
        manifest = {"fps": 30, "height": 720, "shots": [[0, 3]], "landmarks": list(POSE),
                    "frames": [[300, [[[x*4, y*4, c] for x, y, c in POSE.values()]]]]*3}
        cleaned = build_tracks({"frames":frames, "parents":parent}, manifest)["frames"]
        self.assertEqual([set(frame) for frame in frames], [set(frame) for frame in cleaned])


if __name__ == "__main__":
    unittest.main()
