"""Behavioural tests for plan_window_tiles.py (half-lap tiling against a print window).

Pure arithmetic - no Blender, no slicer, no printer. Run:

    python3 -m unittest discover -s <skill>/tests -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'
spec = importlib.util.spec_from_file_location('plan_window_tiles', SCRIPTS / 'plan_window_tiles.py')
pwt = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pwt)


class UnevenLayoutTests(unittest.TestCase):
    def test_every_tile_is_the_same_extent(self):
        lay = pwt.uneven_layout(342.0, 4, 20.0)
        self.assertEqual(len(set(lay['tile_extents'])), 1)
        self.assertAlmostEqual(lay['max_extent'], 100.5, places=3)

    def test_widths_sum_to_the_span(self):
        # Reported widths are rounded for readability, so allow a micron of accumulated rounding -
        # three orders of magnitude below anything an FDM printer can resolve.
        for span, n, lap in ((342.0, 4, 20.0), (355.0, 4, 20.0), (500.0, 7, 30.0)):
            lay = pwt.uneven_layout(span, n, lap)
            self.assertAlmostEqual(sum(lay['widths']), span, delta=1e-4)

    def test_edge_cells_are_half_a_lap_wider(self):
        lay = pwt.uneven_layout(342.0, 4, 20.0)
        self.assertAlmostEqual(lay['widths'][0] - lay['widths'][1], 10.0, places=6)
        self.assertAlmostEqual(lay['widths'][0], lay['widths'][-1], places=6)

    def test_single_tile_has_no_lap_growth(self):
        lay = pwt.uneven_layout(80.0, 1, 20.0)
        self.assertEqual(lay['max_extent'], 80.0)


class EvenLayoutTests(unittest.TestCase):
    def test_interior_tiles_are_larger_than_edge_tiles(self):
        lay = pwt.even_layout(342.0, 4, 20.0)
        self.assertAlmostEqual(lay['tile_extents'][0], 85.5 + 10, places=3)
        self.assertAlmostEqual(lay['tile_extents'][1], 85.5 + 20, places=3)
        self.assertAlmostEqual(lay['max_extent'], 105.5, places=3)

    def test_even_can_need_more_cells_than_uneven_for_the_same_budget(self):
        """The point of the uneven layout: between the two max extents there is a budget band where the
        even grid needs an extra column and the uneven one does not. For 342 mm at a 20 mm lap those are
        105.5 (even) and 100.5 (uneven), so a 103 mm budget separates them."""
        budget = 103.0
        self.assertGreater(pwt.even_layout(342.0, 4, 20.0)['max_extent'], budget)
        self.assertLessEqual(pwt.uneven_layout(342.0, 4, 20.0)['max_extent'], budget)
        self.assertEqual(pwt.min_n(342.0, 20.0, budget), 4)


class MinimumCountTests(unittest.TestCase):
    def test_part_already_inside_the_budget_is_one_tile(self):
        self.assertEqual(pwt.min_n(90.0, 20.0, 106.0), 1)

    def test_known_case(self):
        self.assertEqual(pwt.min_n(342.0, 20.0, 106.0), 4)
        self.assertEqual(pwt.min_n(355.0, 20.0, 119.0), 4)

    def test_result_always_satisfies_the_budget(self):
        for span in (200.0, 342.0, 355.0, 800.0):
            for lap in (10.0, 20.0, 30.0):
                for budget in (60.0, 106.0, 119.0):
                    n = pwt.min_n(span, lap, budget)
                    if n is None:
                        self.assertLessEqual(budget, lap)
                        continue
                    self.assertLessEqual(pwt.uneven_layout(span, n, lap)['max_extent'], budget + 1e-6)
                    if n > 1:
                        self.assertGreater(pwt.uneven_layout(span, n - 1, lap)['max_extent'], budget)

    def test_lap_wider_than_the_budget_is_infeasible(self):
        self.assertIsNone(pwt.min_n(342.0, 120.0, 100.0))


class DiagonalTests(unittest.TestCase):
    def test_45_degree_square_side(self):
        self.assertAlmostEqual(pwt.diagonal_side(214.0, 16.0), 230.0 / math.sqrt(2), places=6)

    def test_rotating_buys_roughly_40_percent_more_length(self):
        budget = 106.0
        longest_square = budget
        longest_diag = budget * math.sqrt(2) - 16.0
        self.assertGreater(longest_diag, longest_square * 1.25)


class CliTests(unittest.TestCase):
    def test_grid_plan_reports_a_feasible_recommendation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'plan.json'
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pwt.main(['--size', '342x355', '--lap', '20', '--window', '117x130',
                               '--raft-margin', '5.5', '--json', str(out)])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text())
            self.assertEqual(data['grid'], [4, 4])
            self.assertAlmostEqual(data['max_tile'][0], 100.5, places=3)
            self.assertIn('checkerboard', buf.getvalue())

    def test_bar_mode_recommends_a_split_when_45_degrees_is_not_enough(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            pwt.main(['--bar', '214x16', '--window', '117x130', '--raft-margin', '5.5'])
        text = buf.getvalue()
        self.assertIn('does NOT fit', text)
        self.assertIn('split into', text)

    def test_bar_mode_accepts_a_bar_that_fits_on_the_diagonal(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = pwt.main(['--bar', '120x16', '--window', '117x130', '--raft-margin', '5.5'])
        self.assertEqual(rc, 0)
        self.assertIn('rotated 45 deg', buf.getvalue())
        self.assertNotIn('split into', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
