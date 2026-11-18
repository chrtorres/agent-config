"""Read-only storage collection, accounting and bounded snapshot persistence."""
import copy
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import threading
import time

LSBLK = ["lsblk", "--json", "--bytes", "--tree", "--exclude", "7", "--output",
         "NAME,KNAME,PATH,MAJ:MIN,TYPE,SIZE,MODEL,TRAN,ROTA,FSTYPE,FSVER,LABEL,UUID,MOUNTPOINTS"]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run(argv, timeout=8):
    started = time.monotonic()
    evidence = {"argv": argv, "started_at": now()}
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env={**os.environ, "LC_ALL": "C"}, check=False)
        evidence.update(exit_code=result.returncode, stderr=result.stderr[:1600])
        output = result.stdout
    except (OSError, subprocess.TimeoutExpired) as error:
        evidence.update(exit_code=None, stderr=str(error)[:1600])
        output = ""
    evidence["duration_ms"] = round((time.monotonic() - started) * 1000)
    return output, evidence


def number(value):
    try:
        result = int(value or 0)
        return max(0, result)
    except (ValueError, TypeError, OverflowError):
        return 0


def accounting(stat):
    total = number(stat.f_blocks) * number(stat.f_frsize)
    free = min(total, number(stat.f_bfree) * number(stat.f_frsize))
    available = min(free, number(stat.f_bavail) * number(stat.f_frsize))
    used = total - free
    reserved = free - available
    denominator = used + available
    return dict(total=total, used=used, available=available, reserved=reserved,
                percent=round(100 * used / denominator, 1) if denominator else None)


def severity(percent):
    if percent is None:
        return "unknown"
    return "critical" if percent >= 90 else "warning" if percent >= 80 else "normal"


def normalize(inventory, stat_reader=os.statvfs, identity_reader=lambda p: os.stat(p).st_dev):
    """Use filesystem identity once across bind mounts and device tree aliases."""
    if not isinstance(inventory, dict) or not isinstance(inventory.get("blockdevices"), list):
        raise ValueError("lsblk returned no blockdevices array")
    nodes, owners, drive_nodes = {}, {}, {}

    def walk(node, owner=None):
        if not isinstance(node, dict):
            raise ValueError("Invalid block device record")
        name = str(node.get("kname") or node.get("name") or "")
        path = str(node.get("path") or ("/dev/" + name))
        if not name or not path.startswith("/dev/"):
            raise ValueError("Invalid device path")
        if node.get("type") == "disk":
            owner = path
            drive_nodes[path] = node
        nodes[path] = node
        if owner:
            owners.setdefault(path, set()).add(owner)
        children = node.get("children") or []
        if not isinstance(children, list):
            raise ValueError("Invalid children array")
        for child in children:
            walk(child, owner)

    for item in inventory["blockdevices"]:
        walk(item)
    volumes, seen, issues = [], {}, []
    for path, node in nodes.items():
        raw_mounts = node.get("mountpoints") or []
        mounts = sorted({m for m in raw_mounts if isinstance(m, str) and m.startswith("/")}, key=lambda m: (len(m), m))
        if not mounts:
            continue
        record = dict(id=path, name=str(node.get("name")), path=path,
                      label=node.get("label") or "", fstype=node.get("fstype") or "unknown",
                      mountpoints=mounts, mountpoint=mounts[0], drive_ids=sorted(owners.get(path, [])),
                      total=None, used=None, available=None, reserved=None, percent=None,
                      severity="unknown", error=None)
        stats = identity = None
        for mount in mounts:
            try:
                stats, identity = stat_reader(mount), identity_reader(mount)
                record["mountpoint"] = mount
                break
            except OSError as error:
                record["error"] = str(error)
        if stats is not None:
            if identity in seen:
                prior = seen[identity]
                prior["mountpoints"] = sorted(set(prior["mountpoints"] + mounts))
                prior["drive_ids"] = sorted(set(prior["drive_ids"] + record["drive_ids"]))
                continue
            record.update(accounting(stats), error=None)
            record["severity"] = severity(record["percent"])
            seen[identity] = record
        else:
            issues.append(f"Usage unavailable for {path}: {record['error']}")
        volumes.append(record)
    partitions = []
    for path, node in nodes.items():
        if node.get("type") == "disk":
            continue
        mounts = [m for m in (node.get("mountpoints") or []) if isinstance(m, str) and m]
        swap = node.get("fstype") == "swap" or "[SWAP]" in mounts
        partitions.append(dict(id=path, name=node.get("name"), path=path, type=node.get("type"),
                               size=number(node.get("size")), fstype=node.get("fstype") or "unknown",
                               label=node.get("label") or "", uuid=node.get("uuid") or "",
                               mountpoints=mounts, drive_ids=sorted(owners.get(path, [])),
                               state="swap" if swap else "mounted" if mounts else "unmounted"))
    drives = []
    for path, node in drive_nodes.items():
        own_volumes = [v for v in volumes if path in v["drive_ids"]]
        known = [v for v in own_volumes if v["total"] is not None and len(v["drive_ids"]) == 1]
        usage = {k: sum(v[k] for v in known) for k in ["total", "used", "available", "reserved"]} if known else None
        if usage:
            denominator = usage["used"] + usage["available"]
            usage["percent"] = round(100 * usage["used"] / denominator, 1) if denominator else None
        drives.append(dict(id=path, name=node.get("kname") or node.get("name"), path=path,
                           model=str(node.get("model") or "Unknown model").strip(), size=number(node.get("size")),
                           transport=node.get("tran") or "unknown", media="HDD" if node.get("rota") else "SSD",
                           partitions=[p for p in partitions if path in p["drive_ids"]],
                           volume_ids=[v["id"] for v in own_volumes], usage=usage,
                           health={"state": "unknown", "reason": "Not collected"}, io=None))
    known_volumes = [v for v in volumes if v["total"] is not None]
    totals = {k: sum(v[k] for v in known_volumes) for k in ["total", "used", "available", "reserved"]}
    totals.update(physical=sum(d["size"] for d in drives), drive_count=len(drives), volume_count=len(volumes),
                  unmounted_count=sum(p["state"] == "unmounted" for p in partitions),
                  unknown_volume_count=sum(v["total"] is None for v in volumes))
    denominator = totals["used"] + totals["available"]
    totals["percent"] = round(100 * totals["used"] / denominator, 1) if denominator else None
    return dict(drives=drives, volumes=volumes, partitions=partitions, totals=totals, issues=issues)


def parse_smart(payload, exit_code):
    if not isinstance(payload, dict):
        return {"state": "unknown", "reason": "Invalid SMART response"}
    if exit_code is None or exit_code & 3:
        metadata = payload.get("smartctl")
        messages = metadata.get("messages", []) if isinstance(metadata, dict) else []
        errors = [m["string"] for m in messages if isinstance(m, dict) and isinstance(m.get("string"), str) and m.get("severity") == "error"] if isinstance(messages, list) else []
        reason = "; ".join(errors[:2])[:500] or "SMART access denied or device could not be opened"
        return {"state": "unavailable", "reason": reason}
    def section(key):
        value = payload.get(key)
        return value if isinstance(value, dict) else {}
    passed = section("smart_status").get("passed")
    result = dict(state="healthy" if passed is True else "failing" if passed is False else "unknown",
                  reason="Device-reported SMART overall status" if isinstance(passed, bool) else "No overall health status returned")
    if exit_code & 4 and passed is not False:
        result.update(state="unknown", reason="SMART command incomplete; health cannot be confirmed")
    if result["state"] == "healthy" and exit_code & 248:
        result.update(state="warning", reason="SMART reports attributes, error log or self-test findings")
    temperature = section("temperature").get("current")
    result["temperature_c"] = temperature if isinstance(temperature, (int, float)) and math.isfinite(temperature) else None
    result["power_on_hours"] = section("power_on_time").get("hours")
    result["percentage_used"] = section("nvme_smart_health_information_log").get("percentage_used")
    return result


def diskstats(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 14:
            try:
                result[fields[2]] = (int(fields[5]) * 512, int(fields[9]) * 512)
            except ValueError:
                continue
    return result


def io_rates(previous, current, elapsed):
    if previous is None or current is None or elapsed <= 0:
        return None
    delta = [current[i] - previous[i] for i in (0, 1)]
    if any(n < 0 for n in delta):
        return None
    return dict(read_bps=round(delta[0] / elapsed, 1), write_bps=round(delta[1] / elapsed, 1))


def findings(snapshot):
    result = []
    for volume in snapshot["volumes"]:
        if volume["severity"] in ("warning", "critical"):
            result.append(dict(kind="capacity", level=volume["severity"], target=volume["id"],
                               title=f"{volume['label'] or volume['path']} is {volume['percent']:g}% used",
                               detail="Review this volume before adding large files. Available space excludes filesystem reserves."))
    for drive in snapshot["drives"]:
        if drive["health"]["state"] in ("failing", "warning"):
            result.append(dict(kind="health", level="critical" if drive["health"]["state"] == "failing" else "warning",
                               target=drive["id"], title=f"Health finding on {drive['name']}", detail=drive["health"]["reason"]))
    return sorted(result, key=lambda f: f["level"] != "critical")


class History:
    def __init__(self, path, limit=720):
        self.path, self.limit = Path(path), limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS samples (id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, payload TEXT NOT NULL)")
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def append(self, sample):
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO samples(captured_at,payload) VALUES (?,?)", (sample["captured_at"], json.dumps(sample)))
            db.execute("DELETE FROM samples WHERE id NOT IN (SELECT id FROM samples ORDER BY id DESC LIMIT ?)", (self.limit,))

    def read(self):
        with self.lock, self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM samples ORDER BY id")]


def history_sample(snapshot):
    rates = [d["io"] for d in snapshot["drives"] if d.get("io") is not None]
    return dict(captured_at=snapshot["captured_at"], used=snapshot["totals"]["used"],
                available=snapshot["totals"]["available"],
                read_bps=sum(r["read_bps"] for r in rates) if rates else None,
                write_bps=sum(r["write_bps"] for r in rates) if rates else None,
                drives=[d["id"] for d in snapshot["drives"]])


class Collector:
    def __init__(self, history):
        self.history = history
        self.lock = threading.Lock()
        self.cached = None
        self.last_time = 0
        self.previous_io = {}
        self.health_cache = {}

    def snapshot(self):
        with self.lock:
            tick = time.monotonic()
            if self.cached and tick - self.last_time < 2:
                return copy.deepcopy(self.cached)
            output, evidence = run(LSBLK)
            if evidence["exit_code"] != 0:
                raise RuntimeError("Storage inventory unavailable: " + evidence["stderr"])
            try:
                data = normalize(json.loads(output))
            except (ValueError, TypeError, KeyError) as error:
                raise RuntimeError("Storage inventory could not be read: " + str(error)) from error
            data.update(schema_version=1, source="live", captured_at=now(), host=socket.gethostname(),
                        evidence=[evidence], issues=data["issues"])
            try:
                raw_io = diskstats(Path("/proc/diskstats").read_text())
                data["evidence"].append({"path": "/proc/diskstats", "status": "read", "sector_bytes": 512})
            except OSError as error:
                raw_io = {}
                data["issues"].append("I/O counters unavailable: " + str(error))
            has_smart = shutil.which("smartctl")
            for drive in data["drives"]:
                drive["io"] = io_rates(self.previous_io.get(drive["name"]), raw_io.get(drive["name"]), tick - self.last_time)
                cached = self.health_cache.get(drive["id"])
                cached_tool = (cached[2].get("argv") or [None])[0] if cached else None
                if cached and (cached[1].get("jit") or (tick - cached[0] < 120 and cached_tool == has_smart)):
                    health, smart_evidence = cached[1:]
                elif not has_smart:
                    health = dict(state="unavailable", reason="smartmontools is not installed; hardware health is unknown")
                    smart_evidence = {"tool": "smartctl", "status": "missing"}
                elif not re.fullmatch(r"/dev/[A-Za-z0-9_.+-]+", drive["path"]):
                    health = dict(state="unavailable", reason="Unsupported device path")
                    smart_evidence = {"tool": "smartctl", "status": "unsupported_path"}
                else:
                    raw, smart_evidence = run([has_smart, "--json", "--all", drive["path"]], timeout=5)
                    try:
                        health = parse_smart(json.loads(raw), smart_evidence["exit_code"])
                    except ValueError:
                        health = dict(state="unavailable", reason="SMART response unavailable; permissions or device support may be required")
                self.health_cache[drive["id"]] = (tick, health, smart_evidence)
                drive["health"] = health
                data["evidence"].append(smart_evidence)
            data["findings"] = findings(data)
            data["totals"]["attention_count"] = len(data["findings"])
            data["coverage"] = dict(usage="partial" if data["issues"] else "complete", hardware_health=sum(d["health"]["state"] in ("healthy", "warning", "failing") for d in data["drives"]))
            try:
                self.history.append(history_sample(data))
            except (OSError, sqlite3.Error) as error:
                data["issues"].append("History could not be saved: " + str(error))
            self.previous_io, self.last_time, self.cached = raw_io, tick, data
            return copy.deepcopy(data)


def demo_snapshot():
    G = 1024 ** 3
    inventory = {"blockdevices": [
        {"name": "nvme0n1", "type": "disk", "size": 1024*G, "model": "Aurora NVMe 1TB", "tran": "nvme", "children": [
            {"name": "nvme0n1p1", "type": "part", "size": G, "fstype": "vfat", "mountpoints": ["/boot/efi"]},
            {"name": "nvme0n1p2", "type": "part", "size": 1023*G, "fstype": "ext4", "label": "System", "mountpoints": ["/"]}]},
        {"name": "sda", "type": "disk", "size": 2*1024*G, "model": "Meridian Archive 2TB", "tran": "sata", "rota": True, "children": [
            {"name": "sda1", "type": "part", "size": 2*1024*G, "fstype": "ext4", "label": "Archive", "mountpoints": ["/mnt/archive"]}]},
        {"name": "sdb", "type": "disk", "size": 512*G, "model": "Pocket SSD 512GB", "tran": "usb", "children": [
            {"name": "sdb1", "type": "part", "size": 500*G, "fstype": "exfat", "label": "Travel", "mountpoints": []}]}]}

    class Stat:
        f_frsize = 1
        def __init__(self, total, used, reserved=0):
            self.f_blocks, self.f_bfree, self.f_bavail = total, total-used, total-used-reserved
    stats = {"/": Stat(1000*G, 622*G, 28*G), "/boot/efi": Stat(G, G//5), "/mnt/archive": Stat(2000*G, 1740*G)}
    data = normalize(inventory, lambda m: stats[m], lambda m: m)
    data.update(schema_version=1, source="demo", captured_at=now(), host="atlas-demo",
                evidence=[{"source": "deterministic fixture", "status": "simulated"}])
    for i, drive in enumerate(data["drives"]):
        drive["health"] = dict(state="healthy" if i < 2 else "unavailable", reason="Simulated SMART status" if i < 2 else "USB adapter does not expose SMART", temperature_c=34+i*3 if i < 2 else None)
        drive["io"] = dict(read_bps=12000000/(i+1), write_bps=3200000/(i+1))
    data["findings"] = findings(data)
    data["totals"]["attention_count"] = len(data["findings"])
    data["coverage"] = {"usage": "complete", "hardware_health": 2}
    return data


def demo_history():
    base = history_sample(demo_snapshot())
    end = dt.datetime.now(dt.timezone.utc)
    return [{**base, "captured_at": (end-dt.timedelta(seconds=(59-i)*10)).isoformat(),
             "read_bps": round((math.sin(i/4)+1.3)*8e6), "write_bps": round((math.cos(i/6)+1.1)*3e6)} for i in range(60)]
