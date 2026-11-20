"""Rebuild browser-authored custom areas from their tracked anatomy anchors."""

from math import isfinite, sqrt
from re import fullmatch


def _number(value):
    return type(value) in (int, float) and isfinite(value)


def validate_points(points, parts):
    if not isinstance(points, dict):
        raise ValueError("Custom areas must be keyed by their IDs")
    for key, point in points.items():
        if not fullmatch(r"point-[1-9]\d*", key) or not isinstance(point, dict):
            raise ValueError("Invalid custom area")
        anchor, segment = point.get("anchor"), point.get("segment")
        if (not isinstance(anchor, str) or anchor not in parts or type(segment) is not int or segment < 0
                or any(not _number(point.get(field)) for field in ("across", "along", "area", "radius"))
                or point["area"] <= 0 or not 4 <= point["radius"] <= 100):
            raise ValueError(f"Invalid tracked anchor for {key}")


def support(point, areas):
    segments = areas.get(point["anchor"], ())
    index = point["segment"]
    if index >= len(segments) or segments[index] is None:
        return None
    x, y, ux, uy, rx, ry = segments[index]
    a, b = point["across"] * rx, point["along"] * ry
    radius = point["radius"] * max(.45, min(2, sqrt(rx * ry / point["area"])))
    return x + a * ux - b * uy, y + a * uy + b * ux, ux, uy, radius, radius
