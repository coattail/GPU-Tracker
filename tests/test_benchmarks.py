import unittest
from contextlib import redirect_stderr
from io import StringIO

import requests

from gpu_monitor.benchmarks import (
    BenchmarkPoint,
    MERCATUS_MODEL_MAP,
    accumulate_benchmark_history,
    collect_mercatus_benchmarks,
    merge_benchmark_series,
)


class FakeMercatusResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "success": True,
            "data": [
                {
                    "fetchDate": "2026-06-10T00:00:00Z",
                    "currentPrice": 2.5,
                }
            ],
        }


class TimeoutThenSuccessSession:
    def __init__(self):
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise requests.exceptions.ReadTimeout("Mercatus timed out")
        return FakeMercatusResponse()


class BenchmarkTests(unittest.TestCase):
    def test_collect_mercatus_skips_timed_out_models(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            series = collect_mercatus_benchmarks(session=TimeoutThenSuccessSession())

        self.assertNotIn("H100", series)
        self.assertIn("H200", series)
        self.assertEqual(series["H200"][0].value, 2.5)
        self.assertIn("Skipping Mercatus benchmark for H100", stderr.getvalue())

    def test_uses_only_unified_benchmark_points(self):
        merged = merge_benchmark_series(
            {"H100": [BenchmarkPoint("2026-05-14", 3.2, "Mercatus GPU Index")]},
            {"H100": [{"date": "2026-05-15", "median": 10.0}]},
        )
        self.assertEqual(merged["H100"][0]["value"], 3.2)
        self.assertEqual(merged["H100"][0]["source"], "Mercatus GPU Index")
        self.assertEqual(merged["H100"][0]["quality"], "unified_daily")

    def test_does_not_fallback_to_mixed_source_history(self):
        merged = merge_benchmark_series({}, {"H200": [{"date": "2026-05-15", "median": 6.3}]})
        self.assertEqual(merged["H200"], [])

    def test_accumulates_history_and_replaces_duplicate_dates(self):
        accumulated = accumulate_benchmark_history(
            {
                "H100": [
                    {
                        "date": "2026-02-13",
                        "value": 3.1,
                        "source": "Mercatus GPU Index",
                        "quality": "unified_daily",
                        "note": "Unified 90-day public series",
                    },
                    {
                        "date": "2026-05-14",
                        "value": 3.2,
                        "source": "Mercatus GPU Index",
                        "quality": "unified_daily",
                        "note": "Unified 90-day public series",
                    },
                ]
            },
            {
                "H100": [
                    BenchmarkPoint("2026-05-14", 3.25, "Mercatus GPU Index"),
                    BenchmarkPoint("2026-05-15", 3.3, "Mercatus GPU Index"),
                ]
            },
            ["H100"],
        )
        self.assertEqual([row["date"] for row in accumulated["H100"]], ["2026-02-13", "2026-05-14", "2026-05-15"])
        self.assertEqual(accumulated["H100"][1]["value"], 3.25)

    def test_tracks_rtx_4090_and_5090_mercatus_series(self):
        self.assertEqual(MERCATUS_MODEL_MAP["RTX 4090"], "RTX_4090")
        self.assertEqual(MERCATUS_MODEL_MAP["RTX 5090"], "RTX_5090")
