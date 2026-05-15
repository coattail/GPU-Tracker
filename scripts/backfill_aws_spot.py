#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gpu_monitor.aggregation import aggregate_observations
from gpu_monitor.benchmarks import collect_mercatus_benchmarks
from gpu_monitor.providers import collect_aws_spot
from gpu_monitor.storage import load_observations, write_snapshot

RAW_DIR = ROOT / "data" / "raw"
AGGREGATED_PATH = ROOT / "data" / "aggregated" / "prices.json"


def main() -> int:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=90)
    result = collect_aws_spot(start_time=start_time, end_time=end_time)
    by_day = defaultdict(list)
    for observation in result.observations:
        by_day[observation.captured_at[:10]].append(observation)

    for day, rows in by_day.items():
        snapshot_path = RAW_DIR / f"{day}.json"
        existing = load_observations([snapshot_path])
        write_snapshot(snapshot_path, [*existing, *rows], errors=[])

    all_observations = load_observations(sorted(RAW_DIR.glob("*.json")))
    AGGREGATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGGREGATED_PATH.write_text(json.dumps(aggregate_observations(all_observations, benchmark_points=collect_mercatus_benchmarks()), ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"days_written": len(by_day), "observations": len(result.observations), "errors": result.errors}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
