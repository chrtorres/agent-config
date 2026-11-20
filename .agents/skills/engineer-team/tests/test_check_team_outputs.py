"""Behavioral tests for scripts/check_team_outputs.py using synthetic plan directories."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("check_team_outputs", HERE.parent / "scripts" / "check_team_outputs.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

FILLER = "Synthetic plan content for tests. " * 20
ROLE_FILES = {
    "ux-research": "01", "visual-design": "02", "frontend-engineering": "03",
    "design-systems": "04", "motion-design": "05", "qa-plan": "06",
}
PM_OK = """# 00 — PM synthesis
## 1. Outcome
x
## 2. Decisions on conflicts
| # | Topic |
## 3. Scope
### P0: must ship
## 4. Implementation sequence
## 5. Definition of done
## 6. Open risks and fallbacks
## Top 5 priorities
1. a
"""


def make_plan(root: Path, skip_role=None, no_top5=None, pm=PM_OK) -> Path:
    plan = root / "plan"
    plan.mkdir()
    (plan / "TEAM-BRIEF.md").write_text("# Brief\n" + FILLER)
    for role, nn in ROLE_FILES.items():
        if role == skip_role:
            continue
        tail = "" if role == no_top5 else "\n## Top 5 priorities\n1. x\n"
        (plan / f"{nn}-{role}.md").write_text(f"# {role}\n{FILLER}{tail}")
    if pm is not None:
        (plan / "00-pm-synthesis.md").write_text(pm)
    return plan


class CheckTeamOutputs(unittest.TestCase):
    def run_main(self, plan, *extra):
        return mod.main([str(plan), *extra])

    def test_complete_round_passes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main(make_plan(Path(d))), 0)

    def test_missing_role_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main(make_plan(Path(d), skip_role="qa-plan")), 1)

    def test_missing_top5_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main(make_plan(Path(d), no_top5="motion-design")), 1)

    def test_pm_missing_section_fails(self):
        with tempfile.TemporaryDirectory() as d:
            pm = PM_OK.replace("## 5. Definition of done\n", "")
            self.assertEqual(self.run_main(make_plan(Path(d), pm=pm)), 1)

    def test_mid_round_without_pm(self):
        with tempfile.TemporaryDirectory() as d:
            plan = make_plan(Path(d), pm=None)
            self.assertEqual(self.run_main(plan), 1)
            self.assertEqual(self.run_main(plan, "--no-pm"), 0)

    def test_custom_roster(self):
        with tempfile.TemporaryDirectory() as d:
            plan = make_plan(Path(d), skip_role="motion-design")
            roles = "ux-research,visual-design,frontend-engineering,design-systems,qa-plan"
            self.assertEqual(self.run_main(plan, "--roles", roles), 0)

    def test_trivial_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            plan = make_plan(Path(d))
            (plan / "03-frontend-engineering.md").write_text("## Top 5 priorities\n")
            self.assertEqual(self.run_main(plan), 1)

    def test_numbered_top5_heading_passes(self):
        with tempfile.TemporaryDirectory() as d:
            plan = make_plan(Path(d))
            (plan / "01-ux-research.md").write_text(f"# ux\n{FILLER}\n## 6. Top 5 priorities\n1. x\n")
            self.assertEqual(self.run_main(plan), 0)

    def test_bad_dir_is_usage_error(self):
        self.assertEqual(self.run_main("/nonexistent/plan-dir-for-test"), 2)


if __name__ == "__main__":
    unittest.main()
