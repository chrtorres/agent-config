"""Verify joint-relative cleanup for visible thigh and shank supports."""
from copy import deepcopy
from pathlib import Path
import math
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from cleanup import compile_cleanup
from cleanup_lower import lower_anchors
from cleanup_tracks import build_tracks, limb_pins


LANDMARKS = [23,25,27,29,31,24,26,28]
BASE = {
    23:(70,40,95),25:(70,85,95),27:(70,135,95),29:(65,139,95),31:(80,142,95),
    24:(97,43,99),26:(101,85,98),28:(111,130,96),
}


def clip(*, gap=None, jitter=None):
    frames=[]
    regions=[]
    for index in range(5):
        dx,dy=index*6,(-6,8,0,9,-1)[index]
        points={key:(x+dx,y+dy,quality) for key,(x,y,quality) in BASE.items()}
        theta=(.14,-.25,.45,-.22,.18)[index]
        kx,ky,_=points[25]
        ux,uy=math.sin(theta),math.cos(theta)
        points[27]=(kx+50*ux,ky+50*uy,95)
        ax,ay,_=points[27]
        points[29]=(ax-4,ay+3,95)
        points[31]=(ax+9,ay+5,95)
        row={key:(round(4*x)/4,round(4*y)/4,quality) for key,(x,y,quality) in points.items()}
        frames.append([200,[[[round(row[key][0]*4),round(row[key][1]*4),row[key][2]] for key in LANDMARKS]]])
        kx,ky,_=row[25]
        ax,ay,_=row[27]
        length=math.hypot(ax-kx,ay-ky)
        ux,uy=(ax-kx)/length,(ay-ky)/length
        noise=.9 if jitter==index else 0
        ellipse=[kx+.43*length*ux-noise*uy,ky+.43*length*uy+noise*ux,
                 -uy,ux,.20*length,.37*length]
        regions.append({"left-calf":[ellipse]} if index!=gap else {})
    return {"frames":regions},{"frames":frames,"landmarks":LANDMARKS,"height":200,"shots":[[0,5]],"fps":30}


class LowerCleanup(unittest.TestCase):
    def test_each_slot_uses_the_observed_side_and_segment(self):
        sample=[0,0,1,0,10,10]
        fields={"left-leg":[sample,None], "right-leg":[sample,sample], "left-calf":[sample]}
        self.assertEqual(lower_anchors(BASE,fields),{
            "left-leg":[[70,40,70,85],None],
            "right-leg":[[97,43,101,85],[101,85,111,130]],
            "left-calf":[[70,85,70,135]],
        })

    def test_unreliable_ankle_does_not_invalidate_the_thigh(self):
        sample=[0,0,1,0,10,10]
        points=dict(BASE)
        points[27]=(70,135,0)
        anchors=lower_anchors(points,{"left-leg":[sample,sample],"left-calf":[sample]})
        self.assertEqual(anchors["left-leg"],[[70,40,70,85],None])
        self.assertEqual(anchors["left-calf"],[None])

    def test_cleanup_preserves_knee_rotation_and_foot_trajectory(self):
        raw,manifest=clip(jitter=2)
        original=deepcopy(manifest)
        output=build_tracks(raw,manifest)["frames"]
        self.assertEqual(manifest,original)
        self.assertNotEqual(output[2]["left-calf"],raw["frames"][2]["left-calf"])
        for index,frame in enumerate(output):
            cx,cy,sx,sy,_,_=frame["left-calf"][0]
            points={key:(x/4,y/4) for key,(x,y,_) in zip(LANDMARKS,manifest["frames"][index][1][0])}
            kx,ky=points[25]
            ax,ay=points[27]
            length=math.hypot(ax-kx,ay-ky)
            ux,uy=(ax-kx)/length,(ay-ky)/length
            # The rotated/timed knee-to-ankle line remains the carrier.
            self.assertAlmostEqual((cx-kx)*ux+(cy-ky)*uy,.43*length,places=2)
            self.assertAlmostEqual(sx*ux+sy*uy,0,places=2)
            xs,ys=np.array([points[key] for key in (27,29,31)]).T
            warp=compile_cleanup([(frame["left-calf"][0],(.75,.75))])
            for delta in warp(xs,ys):
                np.testing.assert_array_equal(delta,np.zeros_like(delta))

    def test_broad_leg_cleanup_pins_observed_joint_and_foot_pixels(self):
        shape=[78,97,1,0,26,51]
        amount=(.75,.75)
        points=dict(BASE)
        points[23]=(70,55,95)
        pins=limb_pins(points,{"left-leg":[shape]},200,200)["left-leg"]
        self.assertEqual([pin[:2] for pin in pins],[list(points[key][:2]) for key in (23,25,27,29,31)])
        fields=[(shape,amount)]
        xs,ys=np.array([pin[:2] for pin in pins],dtype=float).T
        raw=compile_cleanup(fields)(xs,ys)
        self.assertTrue(np.all(np.hypot(*raw)>0))
        pinned=compile_cleanup(fields,{id(amount):pins})
        self.assertTrue(np.all(np.hypot(*pinned(xs,ys))==0))
        self.assertGreater(float(np.hypot(*pinned(np.array([91.]),np.array([112.])))[0]),0)

    def test_visibility_gap_has_no_synthetic_region_or_cross_gap_average(self):
        raw,manifest=clip(gap=2,jitter=1)
        clean=build_tracks(raw,manifest)["frames"]
        self.assertEqual(clean[2],{})
        self.assertEqual(clean[1],raw["frames"][1])
        self.assertEqual(clean[3],raw["frames"][3])


if __name__=="__main__":
    unittest.main()
