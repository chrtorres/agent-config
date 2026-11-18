#!/usr/bin/env python3
"""Local, read-only Linux telemetry and bounded diagnostic jobs. Stdlib only."""
import concurrent.futures
import datetime as dt
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import threading
import time
import uuid


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


# Adapted from system-health-diagnostic: fixed argv, no shell or privilege changes.
CHECKS = {
    "services": ("System services", "startup", ("systemctl", "--failed", "--plain", "--no-legend", "--no-pager")),
    "user-services": ("User services", "startup", ("systemctl", "--user", "--failed", "--plain", "--no-legend", "--no-pager")),
    "boot": ("Boot timing", "startup", ("systemd-analyze", "time")),
    "boot-blame": ("Startup durations", "startup", ("systemd-analyze", "blame", "--no-pager")),
    "capacity": ("Filesystem capacity", "storage", ("df", "-hT", "-x", "squashfs", "-x", "tmpfs")),
    "inodes": ("Root filesystem inodes", "storage", ("df", "-i", "/")),
    "devices": ("Block device layout", "storage", ("lsblk", "-o", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS")),
    "sensors": ("Available temperatures", "storage", ("sensors",)),
    "kernel": ("Recent kernel warnings", "logs", ("journalctl", "-b", "-k", "-p", "warning", "--since=-15min", "--no-pager", "-n", "40")),
    "journal": ("Recent system errors", "logs", ("journalctl", "-b", "-p", "err", "--since=-15min", "--no-pager", "-n", "40")),
    "packages": ("Package installation state", "context", ("dpkg", "--audit")),
    "links": ("Local interface counters", "context", ("ip", "-s", "link")),
    "routes": ("Local routes", "context", ("ip", "route")),
}
PROFILES = {
    "baseline": {"title": "Quick baseline", "checks": ["services", "user-services", "capacity", "inodes", "packages"]},
    "startup": {"title": "Startup & services", "checks": ["services", "user-services", "boot", "boot-blame"]},
    "storage": {"title": "Storage & thermals", "checks": ["capacity", "inodes", "devices", "sensors"]},
    "logs": {"title": "Recent errors", "checks": ["kernel", "journal"]},
    "context": {"title": "Packages & network", "checks": ["packages", "links", "routes"]},
}
GUIDANCE = {
    "startup": "Service durations overlap. Timing alone does not establish the boot critical path. Review the exact failed unit before proposing a repair.",
    "storage": "Capacity is separate from drive health. SMART/NVMe health and vendor thermal limits are unverified in this first pass. No self-tests run.",
    "logs": "At most 40 visible messages per check, from this boot and the last 15 minutes. Journal permissions, rate limiting and truncation can hide events. No entries is not a hardware pass.",
    "context": "Package audit checks installation state, not updates or file integrity. Local routes and counters do not prove Internet connectivity or packet-loss rate.",
}


def run_check(key, cancelled, timeout=8, limit=12000):
    title, category, argv = CHECKS[key]
    result = dict(id=key, title=title, category=category, argv=list(argv),
                  started_at=utc(), status="completed", returncode=None,
                  output="", truncated=False, duration_ms=0)
    start = time.monotonic()
    proc = None
    chunks, size = [], 0
    try:
        if cancelled.is_set():
            result["status"] = "cancelled"
            result.update(interpret(result))
            return result
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True, env={**os.environ, "LC_ALL": "C", "SYSTEMD_COLORS": "0", "SYSTEMD_PAGER": "cat"})
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if cancelled.is_set() or time.monotonic() - start >= timeout:
                    result["status"] = "cancelled" if cancelled.is_set() else "timeout"
                    break
                for stream, _ in selector.select(.05):
                    data = os.read(stream.fd, 4096)
                    if not data:
                        selector.unregister(stream.fd)
                    else:
                        remaining = max(0, limit - size)
                        chunks.append(data[:remaining]) if remaining else None
                        size += len(data)
        # Keep cancellation responsive even if the command closed its output pipe.
        while proc.poll() is None and result["status"] == "completed":
            if cancelled.is_set() or time.monotonic() - start >= timeout:
                result["status"] = "cancelled" if cancelled.is_set() else "timeout"
                break
            cancelled.wait(.05)
        if result["status"] in ("timeout", "cancelled"):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        result["returncode"] = proc.wait()
    except FileNotFoundError:
        result["status"] = "missing"
    except OSError as error:
        result["status"] = "unavailable"
        chunks.append(str(error).encode()[:limit])
    finally:
        if proc and proc.stdout:
            proc.stdout.close()
        result["output"] = b"".join(chunks).decode("utf-8", errors="replace")
        result["truncated"] = size > limit
        result["duration_ms"] = round((time.monotonic() - start) * 1000)
    result.update(interpret(result))
    return result


def interpret(result):
    output = result["output"].strip()
    if result["status"] != "completed" or result["returncode"] != 0:
        return {"assessment": "limited", "summary": "Check unavailable or incomplete; inspect the evidence."}
    if result["truncated"]:
        return {"assessment": "limited", "summary": "Output was capped at 12 KB; evidence is incomplete."}
    if "permission" in output.lower() or "not seeing messages" in output.lower():
        return {"assessment": "limited", "summary": "Access is restricted; the visible output is incomplete."}
    if result["id"] in ("services", "user-services", "packages"):
        return {"assessment": "review" if output else "observed",
                "summary": "Reported items need review." if output else "No issues reported by this check."}
    if result["category"] == "logs":
        empty = not output or output == "-- No entries --"
        return {"assessment": "observed" if empty else "review",
                "summary": "No visible entries in this bounded window." if empty else "Visible log entries need review; they do not establish a root cause."}
    return {"assessment": "observed", "summary": "Collected successfully. Review context before drawing conclusions."}


class Sampler:
    def __init__(self, proc=Path("/proc")):
        self.proc = proc
        self.lock = threading.Lock()
        self.previous = None
        self.process_previous = {}
        self.sequence = 0
        self.cached = None

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            if self.cached and now - self.cached[0] < 1:
                return self.cached[1]
            data = self._read(now)
            self.cached = (now, data)
            return data

    def _read(self, now):
        gaps = []
        cpu, mem, disk, uptime = None, None, None, None
        try:
            ticks = list(map(int, (self.proc / "stat").read_text().splitlines()[0].split()[1:9]))
            total, idle = sum(ticks), ticks[3] + ticks[4]
            if self.previous:
                delta = total - self.previous[0]
                cpu = round(max(0, min(100, 100 * (1 - (idle - self.previous[1]) / delta))), 1) if delta > 0 else None
            self.previous = total, idle
        except (OSError, ValueError, IndexError):
            gaps.append("CPU counters unavailable")
        try:
            values = {line.split(":")[0]: int(line.split()[1]) * 1024
                      for line in (self.proc / "meminfo").read_text().splitlines() if len(line.split()) >= 2}
            total, available = values["MemTotal"], values["MemAvailable"]
            mem = dict(total=total, available=available, used=total-available,
                       percent=round(100*(total-available)/total, 1),
                       swap_used=values.get("SwapTotal", 0)-values.get("SwapFree", 0))
        except (OSError, KeyError, ValueError, ZeroDivisionError):
            gaps.append("Available memory unavailable")
        try:
            fs = os.statvfs("/")
            used, available = (fs.f_blocks-fs.f_bfree)*fs.f_frsize, fs.f_bavail*fs.f_frsize
            disk = dict(mount="/", total=fs.f_blocks*fs.f_frsize, used=used, available=available,
                        percent=round(100*used/max(1, used+available), 1))
        except OSError:
            gaps.append("Root capacity unavailable")
        try:
            uptime = float((self.proc / "uptime").read_text().split()[0])
        except (OSError, ValueError, IndexError):
            gaps.append("Uptime unavailable")
        pressure = {}
        for category in ("cpu", "memory", "io"):
            try:
                row = (self.proc / "pressure" / category).read_text().splitlines()[0].split()
                pressure[category] = float(dict(part.split("=") for part in row[1:])["avg10"])
            except (OSError, KeyError, ValueError, IndexError):
                pressure[category] = None
        processes = self._processes(now, gaps)
        try:
            load = list(os.getloadavg())
        except OSError:
            load = None
        self.sequence += 1
        return dict(source="live", collected_at=utc(), sequence=self.sequence,
                    host=dict(name=platform.node(), system=platform.system(), kernel=platform.release(), cpus=os.cpu_count(),
                              scope="Host-visible /proc; container limits are not normalized."),
                    cpu_percent=cpu, memory=mem, disk=disk, uptime_seconds=uptime,
                    load=load, pressure=pressure, processes=processes, gaps=gaps,
                    reboot_required=Path("/var/run/reboot-required").exists())

    def _processes(self, now, gaps):
        rows, current, skipped = [], {}, 0
        clock, page = os.sysconf("SC_CLK_TCK"), os.sysconf("SC_PAGE_SIZE")
        try:
            directories = sorted((p for p in self.proc.iterdir() if p.name.isdigit()), key=lambda p: int(p.name))
            if len(directories) > 2000:
                gaps.append("Process scan capped at 2,000 PIDs")
            for folder in directories[:2000]:
                try:
                    text = (folder / "stat").read_text()
                    name, rest = text[text.index("(")+1:text.rindex(")")], text[text.rindex(")")+2:].split()
                    ticks, identity = int(rest[11])+int(rest[12]), rest[19]
                    key = folder.name, identity
                    previous = self.process_previous.get(key)
                    percent = round(max(0, 100*(ticks-previous[0])/clock/(now-previous[1])), 1) if previous and now > previous[1] else None
                    current[key] = ticks, now
                    rows.append(dict(pid=int(folder.name), ppid=int(rest[1]), name=name[:100], state=rest[0],
                                     rss=max(0, int(rest[21]))*page, cpu_percent=percent))
                except (OSError, ValueError, IndexError):
                    skipped += 1
        except OSError:
            gaps.append("Process list unavailable")
        if skipped:
            gaps.append(f"{skipped} process entries exited or were inaccessible")
        self.process_previous = current
        return sorted(rows, key=lambda item: item["rss"], reverse=True)[:20]


class Jobs:
    def __init__(self, runner=run_check):
        self.lock = threading.RLock()
        self.current = None
        self.cancelled = threading.Event()
        self.runner = runner
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def start(self, profile, mode):
        if profile not in PROFILES or mode not in ("live", "demo"):
            raise ValueError("Unknown profile or data source")
        with self.lock:
            if self.current and self.current["status"] in ("running", "cancelling"):
                raise RuntimeError("A diagnostic is already running")
            self.cancelled = threading.Event()
            self.current = dict(id=uuid.uuid4().hex, source=mode, profile=profile, title=PROFILES[profile]["title"],
                                started_at=utc(), finished_at=None, status="running", results=[],
                                planned=PROFILES[profile]["checks"], active=None)
            initial = self.get()
            self.executor.submit(self._run, self.current, self.cancelled)
            return initial

    def _run(self, job, cancelled):
        for key in job["planned"]:
            if cancelled.is_set():
                break
            with self.lock:
                job["active"] = key
            if job["source"] == "demo":
                if cancelled.wait(.25):
                    break
                result = demo_check(key)
            else:
                result = self.runner(key, cancelled)
            with self.lock:
                job["results"].append(result)
        with self.lock:
            job.update(status="cancelled" if cancelled.is_set() else "completed", active=None, finished_at=utc())

    def get(self):
        with self.lock:
            return json.loads(json.dumps(self.current))

    def cancel(self, identifier):
        with self.lock:
            if not self.current or self.current["id"] != identifier:
                raise ValueError("Unknown job")
            if self.current["status"] == "running":
                self.current["status"] = "cancelling"
                self.cancelled.set()
            return self.get()

    def close(self):
        self.cancelled.set()
        self.executor.shutdown(wait=True)


def demo_snapshot(sequence=0):
    """Explicit synthetic fixture. Never substitutes for failed live collection."""
    cpu = [22, 27, 24, 38, 32, 25, 19, 24, 28, 23][sequence % 10]
    return dict(source="demo", sequence=sequence, collected_at=utc(),
                host=dict(name="demo-workstation", system="Linux", kernel="synthetic fixture", cpus=8,
                          scope="Synthetic values, no host inspection."),
                cpu_percent=cpu, memory=dict(total=16*1024**3, available=9.6*1024**3, used=6.4*1024**3, percent=40, swap_used=0),
                disk=dict(mount="/", total=512*1024**3, used=445*1024**3, available=67*1024**3, percent=87),
                uptime_seconds=185340+sequence*3, load=[1.42, 1.18, 1.05],
                pressure=dict(cpu=1.2, memory=0, io=.4), gaps=[], reboot_required=False,
                processes=[dict(pid=100+i, ppid=1, name=name, state="S", rss=rss*1024**2, cpu_percent=percent)
                           for i, (name, rss, percent) in enumerate([("browser", 840, 12.4), ("editor", 510, 3.2), ("desktop-shell", 220, 1.8), ("python3", 48, .7)])])


def demo_check(key):
    title, category, argv = CHECKS[key]
    outputs = {"services": "demo-backup.service loaded failed failed Synthetic backup fixture", "capacity": "Filesystem Type Size Used Avail Use% Mounted on\n/dev/demo ext4 512G 445G 67G 87% /", "inodes": "Filesystem Inodes IUsed IFree IUse% Mounted on\n/dev/demo 32000000 510000 31490000 2% /", "boot": "Startup finished in 3.1s (kernel) + 5.6s (userspace) = 8.7s", "boot-blame": "2.1s demo-network.service\n1.2s demo-desktop.service", "devices": "NAME TYPE SIZE FSTYPE MOUNTPOINTS\ndemo disk 512G ext4 /", "kernel": "-- No entries --", "journal": "-- No entries --", "links": "demo0: synthetic interface; no real network observation", "routes": "Synthetic local route fixture"}
    result = dict(id=key, title=title, category=category, argv=list(argv), started_at=utc(),
                  status="missing" if key == "sensors" else "completed", returncode=None if key == "sensors" else 0,
                  output=outputs.get(key, ""), truncated=False, duration_ms=250)
    result.update(interpret(result))
    return result
