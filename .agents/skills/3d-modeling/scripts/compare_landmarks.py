"""Compare calibrated image spans and mesh bounds on corresponding axes."""

import argparse
import json
import math
from pathlib import Path


def measure(bounds, axis, kind):
    low, high = (corner["xyz".index(axis)] for corner in bounds)
    return {"span": high - low, "center": (high + low) / 2, "min": low, "max": high}[kind]


def compare(geometry, landmarks):
    if geometry["units"] != "mm" or not landmarks:
        raise ValueError("Expected millimeter bounds and at least one landmark")
    for landmark in landmarks:
        calibration = landmark["calibration"]
        pixels = calibration["span_px"]
        length = calibration["span_mm"]
        allowance_px = landmark["allowance_px"]
        if not all(math.isfinite(v) and v > 0 for v in (pixels, length, allowance_px)):
            raise ValueError("Calibration spans and allowance must be positive and finite")
        scale = length / pixels
        expected = landmark["reading_px"] * scale
        bounds = geometry["part_bounds_xyz_mm"][landmark["part"]]
        actual = measure(bounds, landmark["axis"], landmark["kind"])
        delta = abs(actual - expected)
        yield {
            "feature": landmark["feature"],
            "basis": landmark["basis"],
            "reference_mm": expected,
            "mesh_mm": actual,
            "absolute_delta_mm": delta,
            "relative_delta": delta / abs(expected) if expected else None,
            "reading_allowance_mm": allowance_px * scale,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geometry", type=Path)
    parser.add_argument("landmarks", type=Path)
    args = parser.parse_args()
    geometry = json.loads(args.geometry.read_text())
    landmarks = json.loads(args.landmarks.read_text())
    print(json.dumps({"features": list(compare(geometry, landmarks)),
                      "overall_fidelity": "unverified"}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
