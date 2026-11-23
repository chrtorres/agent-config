"""Recording-style measurement, matching, rendering pieces and the style library."""
from io import BytesIO
import json
import math
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from zipfile import ZipFile

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
sys.path.insert(0, str(ROOT/"tests"))
sys.path.insert(0, str(ROOT))
import recording_style as rs  # noqa: E402


class CameraPath(unittest.TestCase):
    def test_trend_follows_accelerating_moves_to_the_ends(self):
        x = np.arange(80, dtype=np.float64)
        path = .03*x*x-2*x+5
        np.testing.assert_allclose(rs.trend(path, 12), path, atol=1e-6)

    def test_compose_and_parameters_round_trip(self):
        centre = (320., 180.)
        row = (4.5, -2., math.radians(1.2), math.log(1.03))
        back = rs.parameters([rs.compose(row, centre)], centre)[0]
        np.testing.assert_allclose(back, row, atol=1e-9)

    def test_corrections_put_frames_on_the_smooth_path(self):
        rng = np.random.default_rng(0)
        frames, size, fps = 60, (640, 360), 30.
        centre = (size[0]/2, size[1]/2)
        shake = rng.normal(0, 3, (frames, 2))
        rows = np.c_[np.arange(frames)*4.+shake[:, 0], shake[:, 1], np.radians(rng.normal(0, .3, frames)), np.zeros(frames)]
        path = [rs.compose(row, centre) for row in rows]
        steps = [np.eye(3)]+[path[i] @ np.linalg.inv(path[i-1]) for i in range(1, frames)]
        times = np.arange(frames)/fps
        steady = {"shake": 0., "roll": 0., "frequency": 0., "pan": 0.}
        corrections = rs.camera_corrections(steps, times, times, np.arange(frames), fps, fps, size, steady)
        result = rs.parameters([c @ p for c, p in zip(corrections, rs.cumulative(steps[1:]))], centre)
        residual = result-np.stack([rs.trend(result[:, k], fps/2) for k in range(4)], axis=1)
        self.assertLess(np.abs(residual[:, :2]).max(), .5)
        self.assertLess(np.abs(np.degrees(residual[:, 2])).max(), .05)

    def test_added_shake_has_the_style_amplitude_and_frequency(self):
        motion = {"shake": .6, "roll": .3, "frequency": 2.5, "pan": 0.}
        shake = rs.style_shake(240, 24., 960, motion)
        measured = rs.shake_measures([[rs.compose((dx, dy, da, 0.), (480., 270.)) for dx, dy, da in np.diff(shake, axis=0)]],
                                     24., 960, (480., 270.))
        self.assertAlmostEqual(measured["shake"], .6, delta=.12)
        self.assertAlmostEqual(measured["roll"], .3, delta=.08)
        self.assertAlmostEqual(measured["frequency"], 2.5, delta=.4)


class Measures(unittest.TestCase):
    def test_noise_estimate(self):
        rng = np.random.default_rng(1)
        base = cv2.GaussianBlur(rng.uniform(0, 255, (240, 320)).astype(np.float32), (0, 0), 6)
        for sigma in (0., 3., 8.):
            self.assertAlmostEqual(rs.noise_sigma(base+rng.normal(0, sigma, base.shape)), sigma, delta=.25+.08*sigma)

    def test_vignette_fit_ignores_scenery_and_recovers_the_falloff(self):
        rng = np.random.default_rng(2)
        scene = cv2.GaussianBlur(rng.uniform(20, 80, (400, 700)).astype(np.float32), (0, 0), 3)
        scene[100:180, 400:520] = 15  # a dark object that is not vignetting
        height, width = 180, 320
        falloff = rs.vignette_at([-16., -4.], rs.radius_squared(height, width))
        fit = rs.VignetteFit()
        frames = [scene[40+i:40+i+height, 30+6*i:30+6*i+width]+falloff for i in range(25)]
        for i in range(1, len(frames)):
            fit.add(frames[i-1], frames[i], np.float32([[1, 0, -6], [0, 1, -1]]))
        model = fit.result()
        self.assertIsNotNone(model)
        self.assertAlmostEqual(model[0]+model[1], -20., delta=1.5)

    def test_still_camera_leaves_vignette_unmeasured(self):
        self.assertIsNone(rs.VignetteFit().result())

    def test_lightness_curve_is_monotone_and_maps_quantiles(self):
        source = np.linspace(20, 70, 101)
        target = np.linspace(5, 95, 101)**1.0
        curve = rs.lightness_curve(source, target)
        self.assertTrue(np.all(np.diff(curve) >= -1e-5))
        self.assertAlmostEqual(float(np.interp(45, np.linspace(0, 100, 1001), curve)), 50, delta=1.5)


class Clips(unittest.TestCase):
    """End-to-end measurements on short synthetic clips (a few seconds of work)."""

    @classmethod
    def setUpClass(cls):
        import make_style_clips
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        make_style_clips.SECONDS = 2.
        cls.profiles = {}
        for camera, seed, part in (("film", 1, 0), ("film", 1, 1), ("studio", 3, 0)):
            path = root/f"{camera}-{seed}-{part}.mp4"
            make_style_clips.make(path, camera, seed, part)
            cls.profiles[(camera, part)] = rs.analyse(path)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_profiles_are_valid_and_json_safe(self):
        for profile in self.profiles.values():
            self.assertTrue(rs.valid_profile(json.loads(json.dumps(profile))))

    def test_same_shoot_matches_and_other_camera_does_not(self):
        film, later, studio = self.profiles[("film", 0)], self.profiles[("film", 1)], self.profiles[("studio", 0)]
        self.assertEqual(rs.similarity(film, film)[0], 100.)
        self.assertGreaterEqual(rs.similarity(film, later)[0], rs.MATCH_THRESHOLD)
        self.assertLess(rs.similarity(film, studio)[0], 60)
        self.assertEqual(rs.similarity(film, studio)[0], rs.similarity(studio, film)[0])

    def test_measured_style_reflects_the_camera(self):
        film, studio = self.profiles[("film", 0)], self.profiles[("studio", 0)]
        self.assertEqual((film["format"]["width"], round(film["format"]["fps"])), (960, 24))
        self.assertGreater(film["motion"]["shake"], 3*studio["motion"]["shake"])
        self.assertLess(film["vignette"]["corner"], -8)
        self.assertGreater(film["color"]["neutral_ab"][1], studio["color"]["neutral_ab"][1]+8)
        self.assertGreater(film["audio"]["low_mid"], studio["audio"]["low_mid"]+4)

    def test_damaged_profiles_are_rejected(self):
        broken = json.loads(json.dumps(self.profiles[("film", 0)]))
        broken["color"]["L_quantiles"][3] = float("nan")
        self.assertFalse(rs.valid_profile(broken))
        self.assertFalse(rs.valid_profile({"version": 99}))

    def test_library_reports_an_existing_style_instead_of_adding_it(self):
        from app.style_routes import Library
        with tempfile.TemporaryDirectory() as directory:
            library = Library(Path(directory)/"styles")
            self.assertIsNone(library.export())
            first = library.learn(self.profiles[("film", 0)], "Film look")
            self.assertEqual(first["kind"], "added")
            again = library.learn(self.profiles[("film", 1)], "Film again")
            self.assertEqual(again["kind"], "duplicate")
            self.assertEqual(again["name"], "Film look")
            self.assertGreaterEqual(again["match"], rs.MATCH_THRESHOLD)
            other = library.learn(self.profiles[("studio", 0)], "\x07Studio\n")
            self.assertEqual((other["kind"], other["name"]), ("added", "Studio"))
            self.assertEqual([entry["name"] for entry in library.listing()], ["Film look", "Studio"])
            stored = Path(directory)/"styles"/f"{first['id']}.json"
            self.assertEqual(stat.S_IMODE(stored.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(stored.parent.stat().st_mode), 0o700)
            (stored.parent/"0123456789abcdef.json").write_text("{not json")
            self.assertEqual(len(library.listing()), 2)
            with ZipFile(BytesIO(library.export())) as archive:
                self.assertEqual(set(archive.namelist()), {entry["id"] + ".json" for entry in library.listing()})
                for name in archive.namelist():
                    self.assertEqual(json.loads(archive.read(name)), json.loads((stored.parent/name).read_text()))
            self.assertTrue(library.delete(first["id"]))
            self.assertFalse(library.delete("../../etc/passwd"))
            self.assertEqual([entry["name"] for entry in library.listing()], ["Studio"])


if __name__ == "__main__":
    unittest.main()
