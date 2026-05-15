#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gpu_monitor.benchmarks import accumulate_benchmark_history, collect_mercatus_benchmarks
from gpu_monitor.normalize import TRACKED_GPU_MODELS

AGGREGATED_PATH = ROOT / "data" / "aggregated" / "prices.json"


def load_existing_series() -> dict[str, list[dict]]:
    if not AGGREGATED_PATH.exists():
        return {}
    try:
        payload = json.loads(AGGREGATED_PATH.read_text())
    except json.JSONDecodeError:
        return {}
    return payload.get("benchmark_series", {})


def build_payload() -> dict:
    series = collect_mercatus_benchmarks()
    accumulated_series = accumulate_benchmark_history(load_existing_series(), series, TRACKED_GPU_MODELS)
    latest = max((row["date"] for points in accumulated_series.values() for row in points), default=None)
    return {
        "meta": {
            "generated_at": latest,
            "currency": "USD",
            "unit": "GPU-hour",
            "tracked_gpu_models": list(TRACKED_GPU_MODELS),
            "primary_source": "Mercatus GPU Index",
            "source_window": "90D",
            "history_mode": "accumulated",
        },
        "benchmark_series": accumulated_series,
    }


def main() -> int:
    AGGREGATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    AGGREGATED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "generated_at": payload["meta"]["generated_at"],
                "source": payload["meta"]["primary_source"],
                "models": len(payload["benchmark_series"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
