import base64
import unittest

import cv2
import numpy as np

from tools.face_curvature import depth_bands


class FaceCurvatureTests(unittest.TestCase):
    def test_six_relative_depth_bands_stay_inside_the_semantic_mask(self):
        y, x = np.mgrid[0:1:15j, 0:1:15j]
        points = np.column_stack((x.ravel(), y.ravel(), ((x-.5)**2+(y-.5)**2).ravel()))
        alpha = np.zeros((80, 96), dtype=np.uint8)
        cv2.ellipse(alpha, (45, 40), (26, 23), 0, 0, 360, 220, -1)
        layers = depth_bands(points, (64, 64), np.array([[1., 0., 13.], [0., 1., 8.]]), alpha)
        left, top, width, height = layers["bounds"]
        masks = []
        for png in layers["bands"]:
            layer = cv2.imdecode(np.frombuffer(base64.b64decode(png), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            self.assertEqual(layer.shape, (height, width, 4))
            self.assertTrue(np.any(layer[..., 3]))
            masks.append(layer[..., 3] > 0)
        self.assertEqual(len(masks), 6)
        coverage = np.sum(masks, axis=0)
        self.assertLessEqual(coverage.max(), 1)
        self.assertFalse(np.any((coverage != 0) & (alpha[top:top+height,left:left+width] == 0)))
        self.assertTrue(masks[0][40-top,45-left])
