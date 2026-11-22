"""Report a worker's frame progress to the editor through a small atomic file.

The launcher passes the file path in FOOTAGE_PROGRESS. Without it, reporting is a no-op,
so the tools still run standalone from the command line.
"""
import os
from pathlib import Path
from time import monotonic


def frame_total(stream):
    """Return the expected frame count, estimating from duration when the container omits it."""
    if stream.frames:
        return int(stream.frames)
    if stream.duration and stream.average_rate:
        return max(1, round(float(stream.duration * stream.time_base * stream.average_rate)))
    return 0


class Progress:
    def __init__(self, total=0, path=None, interval=.4):
        location = path if path is not None else os.environ.get("FOOTAGE_PROGRESS")
        self.path = Path(location) if location else None
        self.total = max(0, int(total))
        self.interval = interval
        self.written = 0.
        self.label = ""

    def update(self, done, total=None, force=False, label=None):
        if self.path is None:
            return
        if total is not None:
            self.total = max(0, int(total))
        if label is not None and label != self.label:
            self.label, force = label, True
        now = monotonic()
        # Throttle writes so a fast loop does not spend its time on progress files.
        if not force and now - self.written < self.interval:
            return
        self.written = now
        pending = self.path.with_name(self.path.name + ".partial")
        try:
            pending.write_text(f"{int(done)} {self.total}\n{self.label}".rstrip("\n"))
            pending.replace(self.path)
        except OSError:
            pass

    def finish(self):
        self.update(self.total or 1, self.total or 1, force=True)


def read_progress(path):
    """Read a progress file written by Progress. Return (fraction or None, label)."""
    try:
        counts, _, label = Path(path).read_text().partition("\n")
        done, total = map(int, counts.split())
    except (OSError, ValueError):
        return None, ""
    return (min(1., done / total) if total > 0 else None), label.strip()


class Estimate:
    """Turn a rising 0..1 fraction into a percentage and a remaining-time estimate.

    The rate is measured from the first nonzero sample, so setup time spent at 0%
    (model loading, uploads) does not inflate the estimate.
    """

    def __init__(self):
        self.started = monotonic()
        self.origin = None

    def snapshot(self, fraction):
        if fraction is None:
            return {"percent": None, "eta": None}
        now = monotonic()
        fraction = max(0., min(1., fraction))
        if self.origin is None and fraction > 0:
            self.origin = now, fraction
        eta = None
        if self.origin is not None:
            elapsed, gained = now - self.origin[0], fraction - self.origin[1]
            if elapsed >= 2 and gained >= .01:
                eta = max(0, round(elapsed * (1 - fraction) / gained))
        return {"percent": round(100 * fraction, 1), "eta": eta}


class Tracker(Estimate):
    """Combine weighted per-step progress files (one per worker) into one estimate."""

    def __init__(self, directory, weights):
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.weights = dict(weights)
        self.finished = set()

    def path(self, name):
        return self.directory / f"{name}.progress"

    def finish(self, name):
        self.finished.add(name)

    def fraction(self):
        total = sum(self.weights.values()) or 1
        done = 0.
        for name, weight in self.weights.items():
            share = 1. if name in self.finished else (read_progress(self.path(name))[0] or 0.)
            done += weight * share
        return done / total

    def status(self):
        return self.snapshot(self.fraction())
