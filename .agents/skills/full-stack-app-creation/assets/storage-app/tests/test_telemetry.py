import copy
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from telemetry import (Collector, History, LSBLK, accounting, demo_history, demo_snapshot,
                       diskstats, findings, io_rates, normalize, parse_smart, severity)
from server import make_server


class Stat:
    f_blocks = 1000
    f_bfree = 300
    f_bavail = 250
    f_frsize = 4096


def inventory():
    return {"blockdevices": [{"name": "sda", "type": "disk", "size": 8000000, "children": [
        {"name": "sda1", "type": "part", "size": 4000000, "fstype": "ext4", "mountpoints": ["/", "/bind copy"]},
        {"name": "sda2", "type": "part", "size": 2000000, "fstype": "ntfs", "mountpoints": []},
        {"name": "sda3", "type": "part", "size": 1000000, "fstype": "swap", "mountpoints": ["[SWAP]"]}]}]}


class AccountingTests(unittest.TestCase):
    def test_A02_balance_and_reserved(self):
        usage = accounting(Stat())
        self.assertEqual(usage["total"], usage["used"]+usage["available"]+usage["reserved"])
        self.assertEqual(usage["reserved"], 50*4096)
        self.assertEqual(usage["percent"], 73.7)

    def test_A02_deduplicate_bind_mount_and_device_aliases(self):
        inv = inventory()
        inv["blockdevices"][0]["children"].append({"name": "alias", "type": "crypt", "mountpoints": ["/other"]})
        data = normalize(inv, lambda p: Stat(), lambda p: 42)
        self.assertEqual(len(data["volumes"]), 1)
        self.assertEqual(data["totals"]["total"], Stat.f_blocks*4096)
        self.assertIn("/other", data["volumes"][0]["mountpoints"])
        self.assertEqual(data["totals"]["physical"], 8000000)

    def test_A02_shared_filesystem_not_double_attributed(self):
        shared = {"name": "md0", "type": "raid1", "size": 1000, "mountpoints": ["/raid"]}
        inv = {"blockdevices": [{"name": n, "type": "disk", "size": 1000, "children": [shared]} for n in ["sda", "sdb"]]}
        data = normalize(inv, lambda p: Stat(), lambda p: 1)
        self.assertEqual(data["totals"]["physical"], 2000)
        self.assertEqual(len(data["volumes"]), 1)
        self.assertEqual(len(data["volumes"][0]["drive_ids"]), 2)
        self.assertTrue(all(d["usage"] is None for d in data["drives"]))

    def test_A03_unmounted_and_swap_unknown(self):
        data = normalize(inventory(), lambda p: Stat(), lambda p: 1)
        self.assertEqual(data["totals"]["unmounted_count"], 1)
        self.assertEqual([p["state"] for p in data["partitions"]], ["mounted", "unmounted", "swap"])
        self.assertNotIn("used", data["partitions"][1])

    def test_A16_empty_and_malformed(self):
        self.assertEqual(normalize({"blockdevices": []})["totals"]["percent"], None)
        for value in [None, [], {}, {"blockdevices": {}}, {"blockdevices": [None]}, {"blockdevices": [{"name": "sda", "children": {"bad": True}}]}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value)

    def test_A16_stat_failure_partial(self):
        def unavailable(path):
            raise PermissionError("fixture denied")
        data = normalize(inventory(), unavailable)
        self.assertEqual(data["totals"]["unknown_volume_count"], 1)
        self.assertIsNone(data["volumes"][0]["used"])
        self.assertTrue(data["issues"])

    def test_A16_no_negative_accounting(self):
        stat = Stat()
        stat.f_bavail = -10
        usage = accounting(stat)
        self.assertEqual(usage["available"], 0)
        self.assertEqual(usage["total"], usage["used"]+usage["available"]+usage["reserved"])

    def test_A15_capacity_boundaries(self):
        self.assertEqual([severity(n) for n in [None, 0, 79.9, 80, 89.9, 90, 100]],
                         ["unknown", "normal", "normal", "warning", "warning", "critical", "critical"])
        fixture = demo_snapshot()
        self.assertEqual(len(fixture["findings"]), 1)
        self.assertEqual(fixture["findings"][0]["level"], "warning")
        fixture["volumes"][0].update(percent=99, severity="critical")
        self.assertEqual(findings(fixture)[0]["level"], "critical")


class HealthAndIOTests(unittest.TestCase):
    def test_A04_smart_bitmask_and_truthful_states(self):
        self.assertEqual(parse_smart({"smart_status": {"passed": True}}, 0)["state"], "healthy")
        self.assertEqual(parse_smart({"smart_status": {"passed": False}}, 8)["state"], "failing")
        self.assertEqual(parse_smart({"smart_status": {"passed": True}}, 64)["state"], "warning")
        self.assertEqual(parse_smart({"smart_status": {"passed": True}}, 4)["state"], "unknown")
        self.assertEqual(parse_smart({}, 2)["state"], "unavailable")
        self.assertEqual(parse_smart({}, None)["state"], "unavailable")
        self.assertEqual(parse_smart({}, 0)["state"], "unknown")
        self.assertEqual(parse_smart({"smart_status": None, "temperature": None, "power_on_time": []}, 0)["state"], "unknown")
        denied = {"smartctl": {"messages": [{"severity": "error", "string": "Device open failed: Permission denied"}]}}
        self.assertIn("Permission denied", parse_smart(denied, 2)["reason"])
        self.assertEqual(parse_smart({"smartctl": {"messages": None}}, 2)["state"], "unavailable")

    def test_A04_smart_missing(self):
        with tempfile.TemporaryDirectory() as tmp, patch("telemetry.run", return_value=(json.dumps(inventory()), {"exit_code": 0})), patch("telemetry.shutil.which", return_value=None):
            s = Collector(History(Path(tmp)/"history.db")).snapshot()
            self.assertEqual(s["drives"][0]["health"]["state"], "unavailable")
            self.assertIn("not installed", s["drives"][0]["health"]["reason"])

    def test_A04_tool_installation_invalidates_missing_cache(self):
        def fake_run(argv, **kwargs):
            payload = inventory() if argv == LSBLK else {"smart_status": {"passed": True}}
            return json.dumps(payload), {"exit_code": 0, "argv": argv}
        with tempfile.TemporaryDirectory() as tmp, patch("telemetry.run", side_effect=fake_run):
            collector = Collector(History(Path(tmp)/"history.db"))
            with patch("telemetry.shutil.which", return_value=None), patch("telemetry.time.monotonic", return_value=10):
                self.assertIn("not installed", collector.snapshot()["drives"][0]["health"]["reason"])
            with patch("telemetry.shutil.which", return_value="/usr/sbin/smartctl"), patch("telemetry.time.monotonic", return_value=13):
                self.assertEqual(collector.snapshot()["drives"][0]["health"]["state"], "healthy")
            with patch("telemetry.shutil.which", return_value=None), patch("telemetry.time.monotonic", return_value=16):
                self.assertIn("not installed", collector.snapshot()["drives"][0]["health"]["reason"])

    def test_A05_interval_rates_and_reset(self):
        self.assertIsNone(io_rates(None, (512, 1024), 2))
        self.assertIsNone(io_rates((1024, 1024), (512, 2048), 2))
        self.assertIsNone(io_rates((0, 0), (512, 1024), 0))
        self.assertEqual(io_rates((512, 1024), (1536, 4096), 2), {"read_bps": 512, "write_bps": 1536})
        stats = diskstats("8 0 sda 1 2 10 4 5 6 20 8 9 10 11\nbad\n8 1 bad 1 2 no 4 5 6 20 8 9 10 11")
        self.assertEqual(stats, {"sda": (5120, 10240)})

    def test_A16_collector_error_is_actionable(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = Collector(History(Path(tmp)/"history.db"))
            with patch("telemetry.run", return_value=("", {"exit_code": 1, "stderr": "fixture failed"})), self.assertRaisesRegex(RuntimeError, "fixture failed"):
                collector.snapshot()
            with patch("telemetry.run", return_value=("{malformed", {"exit_code": 0})), self.assertRaisesRegex(RuntimeError, "could not be read"):
                collector.snapshot()


class PersistenceTests(unittest.TestCase):
    def test_A06_service_restart_preserves_http_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = make_server(0, tmp)
            thread = threading.Thread(target=first.serve_forever, daemon=True)
            thread.start()
            with urllib.request.urlopen(f"http://127.0.0.1:{first.server_port}/api/snapshot?source=live", timeout=20) as response:
                snapshot = json.load(response)
            first.shutdown()
            first.server_close()
            thread.join()
            second = make_server(0, tmp)
            thread = threading.Thread(target=second.serve_forever, daemon=True)
            thread.start()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{second.server_port}/api/history?source=live", timeout=20) as response:
                    samples = json.load(response)["samples"]
                self.assertEqual(samples[-1]["captured_at"], snapshot["captured_at"])
                self.assertEqual(samples[-1]["used"], snapshot["totals"]["used"])
            finally:
                second.shutdown()
                second.server_close()
                thread.join()

    def test_A06_restart_and_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"history.db"
            history = History(path, limit=3)
            for i in range(7):
                history.append({"captured_at": str(i), "used": i})
            restarted = History(path, limit=3)
            self.assertEqual([s["used"] for s in restarted.read()], [4, 5, 6])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_A13_demo_separate(self):
        self.assertEqual(demo_snapshot()["source"], "demo")
        self.assertEqual(len(demo_history()), 60)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = make_server(0, cls.temp.name)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, headers=None, method="GET"):
        request = urllib.request.Request(self.origin+path, headers=headers or {}, method=method)
        return urllib.request.urlopen(request, timeout=20)

    def test_A01_real_inventory_over_http(self):
        with self.request("/api/snapshot?source=live") as response:
            snapshot = json.load(response)
        expected = json.loads(subprocess.check_output(LSBLK, text=True))
        def disks(nodes):
            result = set()
            for n in nodes:
                if n["type"] == "disk": result.add((n["path"], n["size"]))
                result.update(disks(n.get("children", [])))
            return result
        self.assertEqual({(d["path"], d["size"]) for d in snapshot["drives"]}, disks(expected["blockdevices"]))
        self.assertEqual(snapshot["source"], "live")
        for v in snapshot["volumes"]:
            if v["total"] is not None:
                self.assertEqual(v["total"], v["used"]+v["available"]+v["reserved"])
                # Capacity is stable even while real filesystem usage changes.
                self.assertEqual(v["total"], accounting(os.statvfs(v["mountpoint"]))["total"])

    @unittest.skipUnless(shutil.which("smartctl"), "Optional smartmontools is not installed")
    def test_A04_installed_smart_matches_live_http(self):
        executable = shutil.which("smartctl")
        with self.request("/api/snapshot?source=live") as response:
            snapshot = json.load(response)
        smart_evidence = {item["argv"][-1]: item for item in snapshot["evidence"] if item.get("argv", [None])[0] == executable}
        record = {"tool": executable, "euid": os.geteuid(), "mode": "Unprivileged live integration; no drive mutations", "drives": []}
        for drive in snapshot["drives"]:
            argv = [executable, "--json", "--all", drive["path"]]
            direct = subprocess.run(argv, capture_output=True, text=True, timeout=8, check=False)
            payload = json.loads(direct.stdout)
            expected = parse_smart(payload, direct.returncode)
            self.assertEqual(drive["health"]["state"], expected["state"])
            self.assertEqual(drive["health"]["reason"], expected["reason"])
            self.assertEqual(smart_evidence[drive["path"]]["exit_code"], direct.returncode)
            self.assertEqual(smart_evidence[drive["path"]]["argv"], argv)
            record["drives"].append({"path": drive["path"], "argv": argv, "exit_code": direct.returncode,
                                      "messages": payload.get("smartctl", {}).get("messages", []),
                                      "health": drive["health"]})
        record["coverage"] = snapshot["coverage"]
        record["hardware_health_verified"] = snapshot["coverage"]["hardware_health"] == len(snapshot["drives"]) and bool(snapshot["drives"])
        directory = os.environ.get("ATLAS_EVIDENCE")
        if directory:
            (Path(directory)/"smart-live.json").write_text(json.dumps(record, indent=2))

    def test_A07_validation_and_read_only(self):
        for path, headers, method, code in [
            ("/api/snapshot?source=bad", {}, "GET", 400),
            ("/api/snapshot?source=live&source=demo", {}, "GET", 400),
            ("/api/snapshot?command=rm", {}, "GET", 400),
            ("/api/health", {"Host": "attacker.example"}, "GET", 403),
            ("/api/health", {"Origin": "https://attacker.example"}, "GET", 403),
            ("/api/snapshot", {}, "POST", 405),
            ("/api/snapshot", {}, "DELETE", 405),
            ("/../telemetry.py", {}, "GET", 404)]:
            with self.subTest(path=path, method=method), self.assertRaises(urllib.error.HTTPError) as cm:
                self.request(path, headers, method)
            self.assertEqual(cm.exception.code, code)
        with self.request("/") as response:
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_A14_export_and_history(self):
        with self.request("/api/snapshot?source=live") as response:
            live = json.load(response)
        with self.request("/api/history?source=live") as response:
            before = json.load(response)["samples"]
        with self.request("/api/export?source=demo") as response:
            exported = json.load(response)
            self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(exported["snapshot"]["source"], "demo")
        with self.request("/api/history?source=live") as response:
            self.assertEqual(json.load(response)["samples"], before)
        with self.request("/api/export?source=live") as response:
            exported = json.load(response)
        self.assertEqual(exported["snapshot"]["captured_at"], live["captured_at"])
        self.assertEqual(exported["history"][-1]["used"], live["totals"]["used"])


if __name__ == "__main__":
    unittest.main()
