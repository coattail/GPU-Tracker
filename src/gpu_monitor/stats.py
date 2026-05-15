from __future__ import annotations

from math import floor
from statistics import median
from typing import Iterable


def percentile(values: Iterable[float], q: float) -> float:
    items = sorted(float(value) for value in values)
    if not items:
        raise ValueError("cannot compute percentile of empty sequence")
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")
    if len(items) == 1:
        return items[0]
    position = (len(items) - 1) * q
    lower = floor(position)
    upper = min(lower + 1, len(items) - 1)
    weight = position - lower
    return items[lower] * (1 - weight) + items[upper] * weight


def summary(values: Iterable[float], *, dynamic: bool) -> dict[str, float | int]:
    items = sorted(float(value) for value in values)
    if not items:
        return {}
    base: dict[str, float | int] = {
        "min": round(items[0], 6),
        "median": round(median(items), 6),
    }
    if dynamic:
        base.update(
            {
                "p25": round(percentile(items, 0.25), 6),
                "p75": round(percentile(items, 0.75), 6),
                "sample_count": len(items),
            }
        )
    else:
        base["max"] = round(items[-1], 6)
    return base
