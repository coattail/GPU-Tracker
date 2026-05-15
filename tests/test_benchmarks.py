import unittest

from gpu_monitor.benchmarks import BenchmarkPoint, accumulate_benchmark_history, merge_benchmark_series


class BenchmarkTests(unittest.TestCase):
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
