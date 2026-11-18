import copy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from monitor import Sampler, Jobs, CHECKS, demo_check, interpret, run_check
from server import MonitorServer


class CollectorTests(unittest.TestCase):
    def test_interval_cpu_available_memory_and_process_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "stat").write_text("cpu 100 0 0 100 0 0 0 0 50 0\n")
            (root / "meminfo").write_text("MemTotal: 1000 kB\nMemAvailable: 700 kB\nMemFree: 50 kB\nSwapTotal: 100 kB\nSwapFree: 80 kB\n")
            (root / "uptime").write_text("120 500")
            pid = root / "123"
            pid.mkdir()
            fields = ["0"]*22
            fields[0], fields[1], fields[11], fields[12], fields[19], fields[21] = "S", "1", "10", "5", "99", "20"
            (pid / "stat").write_text("123 (name with ) paren) " + " ".join(fields))
            sampler = Sampler(root)
            first = sampler._read(10)
            self.assertIsNone(first["cpu_percent"])
            self.assertEqual(first["memory"]["percent"], 30)
            self.assertEqual(first["processes"][0]["name"], "name with ) paren")
            self.assertIsNone(first["processes"][0]["cpu_percent"])
            # Guest CPU is already included in user time; do not count it twice.
            (root / "stat").write_text("cpu 150 0 0 150 0 0 0 0 5000 0\n")
            fields[11] = "20"
            (pid / "stat").write_text("123 (name with ) paren) " + " ".join(fields))
            second = sampler._read(12)
            self.assertEqual(second["cpu_percent"], 50)
            self.assertGreater(second["processes"][0]["cpu_percent"], 0)
            fields[19] = "100"  # reused PID: new identity must not inherit CPU.
            (pid / "stat").write_text("123 (other) " + " ".join(fields))
            self.assertIsNone(sampler._read(15)["processes"][0]["cpu_percent"])

    def test_missing_proc_is_a_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            result = Sampler(Path(folder)).snapshot()
            self.assertIsNone(result["memory"])
            self.assertIsNone(result["cpu_percent"])
            self.assertIn("CPU counters unavailable", result["gaps"])

    def run_fixture(self, code, **kwargs):
        with patch.dict(CHECKS, {"fixture": ("Fixture", "context", (sys.executable, "-c", code))}):
            return run_check("fixture", threading.Event(), **kwargs)

    def test_bounded_output_and_exit_code(self):
        result = self.run_fixture("print('x'*50000); raise SystemExit(7)", limit=12000)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["output"]), 12000)
        self.assertEqual(result["returncode"], 7)
        self.assertEqual(result["assessment"], "limited")

    def test_timeout_and_missing_tool_are_unknowns(self):
        result = self.run_fixture("import time; time.sleep(2)", timeout=.12)
        self.assertEqual(result["status"], "timeout")
        self.assertLess(result["duration_ms"], 1500)
        with patch.dict(CHECKS, {"fixture": ("Fixture", "context", ("/missing-fieldwork-fixture",))}):
            result = run_check("fixture", threading.Event())
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["assessment"], "limited")

    def test_cancel_after_stdout_closes(self):
        event = threading.Event()
        timer = threading.Timer(.15, event.set)
        with patch.dict(CHECKS, {"fixture": ("Fixture", "context", (sys.executable, "-c", "import os,time; os.close(1); os.close(2); time.sleep(3)"))}):
            timer.start()
            result = run_check("fixture", event)
            timer.join()
        self.assertEqual(result["status"], "cancelled")
        self.assertLess(result["duration_ms"], 1500)

    def test_cancel_before_launch_has_no_observed_assessment(self):
        event = threading.Event()
        event.set()
        with patch("monitor.subprocess.Popen") as launch:
            result = run_check("services", event)
        launch.assert_not_called()
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["assessment"], "limited")

    def test_restricted_journal_is_not_a_pass(self):
        result = demo_check("kernel")
        result["output"] = "Hint: You are currently not seeing messages from other users.\n-- No entries --"
        self.assertEqual(interpret(result)["assessment"], "limited")
        result["output"] = "-- No entries --"
        self.assertEqual(interpret(result)["assessment"], "observed")
        self.assertEqual(demo_check("services")["assessment"], "review")


class JobTests(unittest.TestCase):
    def test_cancel_stops_remaining_commands_and_prevents_overlap(self):
        started = threading.Event()
        calls = []
        def runner(key, event):
            calls.append(key)
            started.set()
            event.wait(2)
            return demo_check(key)
        jobs = Jobs(runner)
        try:
            job = jobs.start("baseline", "live")
            self.assertTrue(started.wait(1))
            with self.assertRaises(RuntimeError):
                jobs.start("baseline", "live")
            jobs.cancel(job["id"])
            jobs.close()
            self.assertEqual(jobs.get()["status"], "cancelled")
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(jobs.get()["results"]), 1)
        finally:
            jobs.close()


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MonitorServer()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        connection.request(method, path, json.dumps(body) if body is not None else None, request_headers)
        response = connection.getresponse()
        status, data, metadata = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return status, data, metadata

    def test_real_http_fixture_and_explicit_routes(self):
        status, raw, headers = self.request("GET", "/api/snapshot?mode=demo")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["source"], "demo")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("GET", "/../monitor.py")[0], 404)
        self.assertEqual(self.request("GET", "/api/snapshot?mode=other")[0], 400)

    def test_cross_origin_and_dns_rebinding_rejected(self):
        self.assertEqual(self.request("GET", "/api/config", headers={"Host": "attacker.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/jobs", {"profile": "baseline", "mode": "live"}, {"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.request("GET", "/api/config", headers={"Sec-Fetch-Site": "cross-site"})[0], 403)

    def test_arbitrary_commands_and_unknown_fields_rejected(self):
        for body in [{"profile": "reboot", "mode": "live"}, {"profile": "baseline", "mode": "live", "argv": ["touch", "bad"]}, {"profile": [], "mode": "live"}, ["baseline"]]:
            self.assertEqual(self.request("POST", "/api/jobs", body)[0], 400)

    def test_demo_job_over_http_never_calls_live_runner(self):
        with patch.object(self.server.jobs, "runner", side_effect=AssertionError("Demo invoked live command")):
            status, raw, _ = self.request("POST", "/api/jobs", {"profile": "logs", "mode": "demo"})
            self.assertEqual(status, 202)
            deadline = time.monotonic()+3
            while time.monotonic() < deadline:
                job = json.loads(self.request("GET", "/api/job")[1])
                if job["status"] == "completed":
                    break
                time.sleep(.03)
            self.assertEqual(job["status"], "completed")
            self.assertEqual(len(job["results"]), 2)
            self.assertEqual(job["source"], "demo")


if __name__ == "__main__":
    unittest.main()
