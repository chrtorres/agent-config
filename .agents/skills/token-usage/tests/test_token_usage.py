import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("token_usage", Path(__file__).parents[1] / "scripts/token_usage.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UsageTests(unittest.TestCase):
    def read(self, totals, tail=""):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            lines = [json.dumps({"type": "event_msg", "payload": {
                "type": "token_count", "info": {"total_token_usage": {
                    "input_tokens": total - 10, "cached_input_tokens": 20,
                    "output_tokens": 10, "reasoning_output_tokens": 2,
                    "total_tokens": total}}}}) for total in totals]
            path.write_text("\n".join(lines) + "\n" + tail)
            return module.snapshot(path)

    def test_cumulative_snapshots_not_summed(self):
        result = self.read([100, 100, 150])
        self.assertEqual(result["total_token_usage"]["total_tokens"], 150)
        self.assertEqual(result["total_token_usage"]["input_tokens"], 140)

    def test_partial_line_preserves_latest_valid_counter(self):
        result = self.read([100], '{"unfinished":')
        self.assertEqual(result["total_token_usage"]["total_tokens"], 100)
        self.assertEqual(result["malformed_lines"], 1)

    def test_counter_reset_is_disclosed(self):
        self.assertEqual(self.read([150, 100])["counter_regressions"], 1)

    def test_absent_telemetry_not_zero(self):
        with self.assertRaises(ValueError):
            self.read([])


if __name__ == "__main__":
    unittest.main()
