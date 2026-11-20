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
        fields = [([20,35,1,0,12,20],(-.4,.2)),([50,42,1,0,12,15],(.25,-.2))]
        y,x = np.mgrid[:75,:75].astype(np.float32)
        for raw,clean in zip(displacement(x,y,fields),compile_cleanup(fields)(x,y)):
            np.testing.assert_array_equal(raw,clean)

    def test_strong_isolated_control_is_relieved_locally(self):
        fields = [([36,35,1,0,24,22],(.75,0))]
        y,x = np.mgrid[:75,:75].astype(np.float32)
        raw,_ = displacement(x,y,fields)
        clean,_ = compile_cleanup(fields)(x,y)
        self.assertLess(abs(clean[35,42]),abs(raw[35,42]))
        self.assertGreater(abs(clean[35,42]),0)
        np.testing.assert_array_equal(raw[:9],clean[:9])

    def test_overlaps_reduce_compression(self):
        fields = [([36,35,1,0,24,22],(-.54,.11)),([40,36,1,0,19,19],(-.53,.18))]
        y,x = np.mgrid[:75,:75].astype(np.float32)
        def determinants(delta):
            dx,dy = delta
            dxy,dxx = np.gradient(dx)
            dyy,dyx = np.gradient(dy)
            return (1+dxx)*(1+dyy)-dxy*dyx
        raw = determinants(displacement(x,y,fields))
        cleaned = determinants(compile_cleanup(fields)(x,y))
        self.assertLess(float(raw.min()),0)
        self.assertGreater(float(cleaned.min()),.25)
        np.testing.assert_array_equal(raw[:9],cleaned[:9])


if __name__=="__main__":
    unittest.main()
