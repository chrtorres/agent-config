"""Regression checks for the Python export's finite support and tone mask."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from cleanup import reach
from export_edit import bounded_remap, displacement, grade
from point_regions import support, validate_points


class EditMath(unittest.TestCase):
    def test_zero_tone_round_trips_full_channel_range(self):
        rgb = np.arange(256,dtype=np.uint8).reshape(16,16,1).repeat(3,axis=2)
        self.assertTrue(np.array_equal(grade(rgb,np.ones((16,16)),[0,0,0]),rgb))

    def test_grade_changes_only_skin(self):
        rgb = np.tile(np.uint8([130,105,92]),(5,5,1))
        skin = np.zeros((5,5),np.float32)
        skin[2,2] = 1
        graded = grade(rgb,skin,[.3,.2,.1])
        self.assertTrue(np.array_equal(graded[skin==0],rgb[skin==0]))
        self.assertFalse(np.array_equal(graded[2,2],rgb[2,2]))

    def test_displacement_stops_at_support_reach(self):
        amount = (.5,0)
        x,y = np.float32([40,50,60,50+20*reach(amount)]),np.float32([50]*4)
        dx,dy = displacement(x,y,[([50,50,1,0,20,10],amount)])
        self.assertLess(dx[0],0)
        self.assertGreater(dx[2],0)
        self.assertEqual(dx[3],0)
        self.assertTrue(np.array_equal(dy,np.zeros_like(dy)))

    def test_shape_preserves_pixels_away_from_region(self):
        y,x = np.mgrid[:80,:80]
        rgb = np.stack((x*3,y*3,(x+y)*1.5),axis=-1).astype(np.uint8)
        moved = bounded_remap(rgb.copy(),np.ones((80,80),np.float32),
                              [([40,40,1,0,20,15],[.65,0])])
        # Rows beyond reach() of the 15 px vertical radius stay untouched.
        self.assertTrue(np.array_equal(moved[:4],rgb[:4]))
        self.assertFalse(np.array_equal(moved[30:55,31:55],rgb[30:55,31:55]))

    def test_custom_export_uses_rotated_anchor_and_larger_range(self):
        point = {"anchor": "arm", "segment": 0, "across": .5, "along": -.25, "area": 200, "radius": 10}
        validate_points({"point-1": point}, {"arm": "Arm"})
        field = support(point, {"arm": [[30, 40, 0, 1, 10, 20]]})
        self.assertEqual(field, (35, 45, 0, 1, 10, 10))
        self.assertIsNone(support(point, {"arm": [None]}))
        y,x = np.mgrid[:80,:80]
        rgb = np.stack((x*3,y*3,(x+y)*1.5),axis=-1).astype(np.uint8)
        moved = bounded_remap(rgb.copy(),np.ones((80,80),np.float32),[(field,(1.1,-.7))],clean=True)
        self.assertTrue(np.array_equal(moved[:14],rgb[:14]))
        self.assertFalse(np.array_equal(moved[38:52,29:42],rgb[38:52,29:42]))


if __name__=="__main__":
    unittest.main()
