import unittest

from gpu_monitor.benchmarks import BenchmarkPoint, merge_benchmark_series


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
