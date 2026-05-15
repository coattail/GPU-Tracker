#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gpu_monitor.benchmarks import collect_mercatus_benchmarks
from gpu_monitor.normalize import TRACKED_GPU_MODELS

AGGREGATED_PATH = ROOT / "data" / "aggregated" / "prices.json"


def build_payload() -> dict:
    series = collect_mercatus_benchmarks()
    latest = max((point.date for points in series.values() for point in points), default=None)
    return {
        "meta": {
            "generated_at": latest,
            "currency": "USD",
            "unit": "GPU-hour",
            "tracked_gpu_models": list(TRACKED_GPU_MODELS),
            "primary_source": "Mercatus GPU Index",
            "history_window": "90D",
        },
        "benchmark_series": {
            model: [
                {
                    "date": point.date,
                    "value": point.value,
                    "source": point.source,
                    "quality": point.quality,
                    "note": "Unified 90-day public series",
                }
                for point in series.get(model, [])
            ]
            for model in TRACKED_GPU_MODELS
        },
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
