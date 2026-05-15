from __future__ import annotations

import html
import json
import re
from pathlib import Path

import requests

WAYBACK_H100_SNAPSHOTS = (
    "20251125140504",
    "20251229175418",
    "20260209191213",
    "20260313073322",
)


def _extract_indexes(document: str) -> dict[str, float]:
    decoded = html.unescape(document)
    match = re.search(r'\\"data\\":\{.*?\\"indexes\\":\{([^}]*)\}', decoded)
    if not match:
        return {}
    payload = json.loads("{" + match.group(1).replace('\\"', '"') + "}")
    return {date: float(value) for date, value in payload.items() if float(value) > 0}


def collect_wayback_h100_history(session: requests.Session | None = None) -> list[dict]:
    session = session or requests.Session()
    merged: dict[str, dict] = {}
    for snapshot in WAYBACK_H100_SNAPSHOTS:
        response = session.get(
            f"https://web.archive.org/web/{snapshot}id_/https://portal.silicondata.com/gpu-index-chart",
            timeout=60,
        )
        response.raise_for_status()
        for date, value in _extract_indexes(response.text).items():
            merged[date] = {
                "date": date,
                "value": value,
                "source": "Silicon Data via Wayback",
                "quality": "daily_public_snapshot",
                "note": f"Archived rolling-window snapshot {snapshot}",
            }
    return [merged[key] for key in sorted(merged)]


def load_manual_benchmarks(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())
