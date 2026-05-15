from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from .models import PriceObservation
from .normalize import TRACKED_GPU_MODELS
from .benchmarks import merge_benchmark_series
from .stats import summary


def _date_key(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()


def aggregate_observations(
    observations: Iterable[PriceObservation],
    *,
    benchmark_points: dict[str, list] | None = None,
) -> dict:
    rows = list(observations)
    grouped: dict[tuple[str, str, str], list[PriceObservation]] = defaultdict(list)
    latest_by_model: dict[str, list[PriceObservation]] = defaultdict(list)
    latest_date_by_model: dict[str, str] = {}

    for row in rows:
        date_key = _date_key(row.captured_at)
        grouped[(row.gpu_model, row.price_type, date_key)].append(row)
        if row.gpu_model not in latest_date_by_model or date_key > latest_date_by_model[row.gpu_model]:
            latest_date_by_model[row.gpu_model] = date_key
            latest_by_model[row.gpu_model] = [row]
        elif date_key == latest_date_by_model[row.gpu_model]:
            latest_by_model[row.gpu_model].append(row)

    series: dict[str, dict[str, list[dict]]] = {
        model: {"list": [], "spot": [], "marketplace": []} for model in TRACKED_GPU_MODELS
    }
    for (model, price_type, date_key), bucket in sorted(grouped.items()):
        stats = summary(
            [row.price_per_gpu_hour_usd for row in bucket],
            dynamic=price_type in {"spot", "marketplace"},
        )
        series.setdefault(model, {"list": [], "spot": [], "marketplace": []})[price_type].append(
            {"date": date_key, **stats}
        )

    latest: dict[str, dict] = {}
    for model in TRACKED_GPU_MODELS:
        bucket = latest_by_model.get(model, [])
        latest[model] = {
            "date": latest_date_by_model.get(model),
            "list": summary(
                [row.price_per_gpu_hour_usd for row in bucket if row.price_type == "list"],
                dynamic=False,
            ),
            "spot": summary(
                [row.price_per_gpu_hour_usd for row in bucket if row.price_type == "spot"],
                dynamic=True,
            ),
            "marketplace": summary(
                [row.price_per_gpu_hour_usd for row in bucket if row.price_type == "marketplace"],
                dynamic=True,
            ),
        }

    details = [row.to_dict() for row in sorted(rows, key=lambda item: item.captured_at)]
    latest_capture = max((row.captured_at for row in rows), default=None)
    fallback_benchmarks = {model: series.get(model, {}).get("list", []) for model in TRACKED_GPU_MODELS}
    benchmark_series = merge_benchmark_series(benchmark_points or {}, fallback_benchmarks)
    return {
        "meta": {
            "generated_at": latest_capture,
            "currency": "USD",
            "unit": "GPU-hour",
            "tracked_gpu_models": list(TRACKED_GPU_MODELS),
        },
        "series": series,
        "benchmark_series": benchmark_series,
        "latest": latest,
        "details": details,
    }
