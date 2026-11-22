"""Check that cleanup changes the overlap without changing isolated warps."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from cleanup import compile_cleanup
from export_edit import displacement


class CleanupMath(unittest.TestCase):
    def test_single_multisegment_feature_is_exact(self):
        adjustment = (-.4,.31)
        fields = [([25,35,1,0,20,33],adjustment),([31,48,0,1,18,23],adjustment)]
        y,x = np.mgrid[:75,:75].astype(np.float32)
        expected = displacement(x,y,fields)
        actual = compile_cleanup(fields)(x,y)
        for before,after in zip(expected,actual):
            np.testing.assert_array_equal(before,after)

    def test_disjoint_features_keep_requested_deformation(self):
        fields = [([20,35,1,0,12,20],(-.4,.2)),([80,42,1,0,12,15],(.25,-.2))]
        y,x = np.mgrid[:75,:100].astype(np.float32)
        for raw,clean in zip(displacement(x,y,fields),compile_cleanup(fields)(x,y)):
            np.testing.assert_array_equal(raw,clean)

    def test_strong_isolated_control_is_relieved_locally(self):
        fields = [([100,100,1,0,24,22],(.75,0))]
        y,x = np.mgrid[:200,:200].astype(np.float32)
        raw,_ = displacement(x,y,fields)
        clean,_ = compile_cleanup(fields)(x,y)
        self.assertLess(abs(clean[100,107]),abs(raw[100,107]))
        self.assertGreater(abs(clean[100,107]),0)
        np.testing.assert_array_equal(raw[:40],clean[:40])

    def test_overlaps_reduce_compression(self):
        fields = [([100,100,1,0,24,22],(-.54,.11)),([104,101,1,0,19,19],(-.53,.18))]
        y,x = np.mgrid[:200,:200].astype(np.float32)
        def determinants(delta):
            dx,dy = delta
            dxy,dxx = np.gradient(dx)
            dyy,dyx = np.gradient(dy)
            return (1+dxx)*(1+dyy)-dxy*dyx
        raw = determinants(displacement(x,y,fields))
        cleaned = determinants(compile_cleanup(fields)(x,y))
        self.assertLess(float(raw.min()),0)
        # The browser mesh accepts triangles down to 0.151 of their area.
        self.assertGreater(float(cleaned.min()),.151)
        np.testing.assert_array_equal(raw[:40],cleaned[:40])

    def test_part_interior_scales_uniformly(self):
        # A real size change keeps one scale across the part. The earlier
        # lens kernel magnified the middle and squeezed the rim.
        fields = [([100,100,.8,.6,30,40],(.5,-.3))]
        y,x = np.mgrid[:200,:200].astype(np.float64)
        dx,dy = displacement(x,y,fields)
        across = (x-100)*.8+(y-100)*.6
        along = (y-100)*.8-(x-100)*.6
        core = (across/30)**2+(along/40)**2 < .85**2
        np.testing.assert_allclose(dx[core],(across*.5*.8+along*.3*.6)[core],atol=1e-9)
        np.testing.assert_allclose(dy[core],(across*.5*.6-along*.3*.8)[core],atol=1e-9)

    def test_surroundings_never_fold(self):
        y,x = np.mgrid[:400,:400].astype(np.float64)*.5
        for amount in ((1.1,1.1),(1.1,-.7),(-.7,-.7),(.4,0)):
            dx,dy = displacement(x,y,[([100,100,1,0,14,20],amount)])
            dxy,dxx = np.gradient(dx,.5)
            dyy,dyx = np.gradient(dy,.5)
            # Only the requested shrink itself may go below the ring's bound.
            requested = (1+amount[0])*(1+amount[1])
            self.assertGreater(float(((1+dxx)*(1+dyy)-dxy*dyx).min()),min(.2,requested-1e-6))


if __name__=="__main__":
    unittest.main()
