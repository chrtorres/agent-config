"""Run unittest and retain per-scenario outcomes for the acceptance rubric."""
import json
import os
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
records = []


class Result(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        records.append({"test": test.id(), "passed": True})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        records.append({"test": test.id(), "passed": False})

    def addError(self, test, error):
        super().addError(test, error)
        records.append({"test": test.id(), "passed": False})


result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(unittest.defaultTestLoader.discover("tests", pattern="test_*.py"))
scenarios = {}
for record in records:
    code = re.search(r"A\d{2}", record["test"])
    if code:
        key = code.group()
        scenarios[key] = scenarios.get(key, True) and record["passed"]
output = os.environ.get("ATLAS_EVIDENCE")
if output:
    (Path(output)/"backend-results.json").write_text(json.dumps({"passed": result.wasSuccessful(), "tests": records, "scenarios": scenarios}, indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
