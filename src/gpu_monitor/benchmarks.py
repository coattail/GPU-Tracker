from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import requests


@dataclass(frozen=True)
class BenchmarkPoint:
    date: str
    value: float
    source: str
    quality: str = "unified_daily"


MERCATUS_MODEL_MAP = {
    "H100": "H100",
    "H200": "H200",
    "B200": "B200",
    "B300": "B300",
    "A100 80GB": "A100_80GB",
    "L40S": "L40S",
    "RTX 4090": "RTX_4090",
    "RTX 5090": "RTX_5090",
}


def collect_mercatus_benchmarks(
    session: requests.Session | None = None,
    *,
    range_name: str = "90D",
) -> dict[str, list[BenchmarkPoint]]:
    session = session or requests.Session()
    result: dict[str, list[BenchmarkPoint]] = {}
    for model, mercatus_model in MERCATUS_MODEL_MAP.items():
        response = session.get(
            "https://www.mercatus-ai.com/api/gpu/trend",
            params={"range": range_name, "baseModel": mercatus_model},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(payload.get("error", {}).get("message") or "Mercatus API failed")
        result[model] = [
            BenchmarkPoint(
                date=row["fetchDate"][:10],
                value=float(row["currentPrice"]),
                source="Mercatus GPU Index",
            )
            for row in payload.get("data", [])
            if row.get("currentPrice") is not None
        ]
    return result


def merge_benchmark_series(
    benchmark_points: dict[str, Iterable[BenchmarkPoint]],
    fallback_series: dict[str, list[dict]],
) -> dict[str, list[dict]]:
    merged: dict[str, list[dict]] = {}
    for model in fallback_series:
        public_points = list(benchmark_points.get(model, []))
        merged[model] = [
            {
                "date": point.date,
                "value": point.value,
                "source": point.source,
                "quality": point.quality,
                "note": "Unified 90-day public series",
            }
            for point in public_points
        ]
    return merged


def accumulate_benchmark_history(
    existing_series: dict[str, list[dict]],
    benchmark_points: dict[str, Iterable[BenchmarkPoint]],
    models: Iterable[str],
) -> dict[str, list[dict]]:
    accumulated: dict[str, list[dict]] = {}
    for model in models:
        by_date = {row["date"]: row for row in existing_series.get(model, []) if row.get("date")}
        for point in benchmark_points.get(model, []):
            by_date[point.date] = {
                "date": point.date,
                "value": point.value,
                "source": point.source,
                "quality": point.quality,
                "note": "Unified 90-day public series",
            }
        accumulated[model] = [by_date[date] for date in sorted(by_date)]
    return accumulated
