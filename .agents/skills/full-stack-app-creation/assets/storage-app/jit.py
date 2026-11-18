"""One-shot privileged SMART reads using the desktop's native polkit agent."""
import copy
import json
import re
import shutil
from pathlib import Path
import threading
from telemetry import now, parse_smart, run


class SmartScan:
    def __init__(self, collector):
        self.collector = collector
        self.lock = threading.Lock()
        self.job = {"state": "idle", "message": "Ready for a user-authorized scan", "results": []}

    def status(self):
        with self.lock:
            return copy.deepcopy(self.job)

    def start(self):
        with self.lock:
            if self.job["state"] == "running":
                raise RuntimeError("A SMART scan is already running")
            self.job = {"state": "running", "message": "Preparing system authentication…", "results": [], "started_at": now()}
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            # Only distribution-installed, root-owned executables are elevated.
            pkexec = shutil.which("pkexec")
            smartctl = shutil.which("smartctl")
            if not pkexec or not smartctl:
                raise RuntimeError("System pkexec and smartctl are required")
            pkexec, smartctl = str(Path(pkexec).resolve()), str(Path(smartctl).resolve())
            for executable in (pkexec, smartctl):
                path = Path(executable).resolve(strict=True)
                for ancestor in (path, *path.parents):
                    stat = ancestor.stat()
                    if stat.st_uid != 0 or stat.st_mode & 0o022:
                        raise RuntimeError("Unsafe system executable ownership or permissions")
            drives = self.collector.snapshot()["drives"]
            for drive in drives:
                if not re.fullmatch(r"/dev/[A-Za-z0-9_.+-]+", drive["path"]):
                    continue
                with self.lock:
                    self.job["message"] = f"Approve the system prompt to read {drive['path']}. Cancel stops this scan."
                argv = [pkexec, "--disable-internal-agent", smartctl, "--json", "--all", drive["path"]]
                raw, evidence = run(argv, timeout=120)
                if evidence["exit_code"] in (126, 127) or evidence["exit_code"] is None:
                    with self.lock:
                        self.job.update(state="cancelled", message="Authorization cancelled, unavailable, or timed out. No further prompts will open.")
                    return
                try:
                    health = parse_smart(json.loads(raw), evidence["exit_code"])
                except ValueError:
                    raise RuntimeError("SMART returned an unreadable response")
                health.update(jit=True, collected_at=now())
                # Retain data for this process session, never retain credentials.
                with self.collector.lock:
                    self.collector.health_cache[drive["id"]] = (0, health, evidence)
                    self.collector.cached = None
                with self.lock:
                    self.job["results"].append({"path": drive["path"], "health": health})
            with self.lock:
                self.job.update(state="complete", message="Scan complete. Readings remain visible for this session; each reading shows its collection time.", finished_at=now())
        except Exception as error:
            with self.lock:
                self.job.update(state="error", message=str(error))
