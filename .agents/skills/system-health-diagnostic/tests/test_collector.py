import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'collector', Path(__file__).resolve().parents[1] / 'scripts/collect_health.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CollectorTests(unittest.TestCase):
    @patch.object(collector.subprocess, 'run')
    def test_failed_command_is_not_reported_as_healthy(self, run):
        run.return_value = subprocess.CompletedProcess(['systemctl'], 3, '', 'failed')
        result = collector.collect(('systemctl', '--failed'))
        self.assertEqual(result['returncode'], 3)
        self.assertEqual(result['output'], 'failed')
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertEqual(run.call_count, 1)

    @patch.object(collector.subprocess, 'run', side_effect=FileNotFoundError)
    def test_missing_tool_is_coverage_gap(self, run):
        result = collector.collect(('sensors',))
        self.assertEqual(result['status'], 'missing')
        self.assertIsNone(result['returncode'])

    @patch.object(collector.subprocess, 'run', side_effect=subprocess.TimeoutExpired('x', 1))
    def test_timeout_does_not_retry(self, run):
        self.assertEqual(collector.collect(('uptime',))['status'], 'timeout')
        self.assertEqual(run.call_count, 1)

    @patch.object(collector.subprocess, 'run')
    def test_large_output_is_marked_truncated(self, run):
        run.return_value = subprocess.CompletedProcess(['x'], 0, '123456', '')
        result = collector.collect(('x',), limit=3)
        self.assertEqual(result['output'], '123')
        self.assertTrue(result['truncated'])


if __name__ == '__main__':
    unittest.main()
