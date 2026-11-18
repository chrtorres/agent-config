import pathlib
import subprocess
import sys
import unittest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
RUNNER = SKILL_DIR / "scripts" / "run_interactive_review_smoke.py"
GENERATOR = SKILL_DIR / "scripts" / "smoke_model_generator.py"


class InteractiveSmokeRunnerTests(unittest.TestCase):
    def test_runner_help_is_available(self):
        result = subprocess.run([sys.executable, str(RUNNER), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("retained", result.stdout)

    def test_generator_and_runner_are_portable(self):
        for path in (RUNNER, GENERATOR):
            text = path.read_text()
            self.assertNotIn("/home/", text)
            self.assertNotIn("/Users/", text)


if __name__ == "__main__":
    unittest.main()
