import json
import math
import pathlib
import unittest
from datetime import date

from gpu_monitor.normalize import TRACKED_GPU_MODELS

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HistorySnapshotTests(unittest.TestCase):
    def test_every_tracked_model_retains_verified_backfill(self):
        payload = json.loads((ROOT / "data/aggregated/prices.json").read_text())
        self.assertEqual(payload["meta"]["source_window"], "ALL")
        for model in TRACKED_GPU_MODELS:
            with self.subTest(model=model):
                rows = payload["benchmark_series"][model]
                dates = [row["date"] for row in rows]
                self.assertGreaterEqual(len(rows), 306)
                self.assertLessEqual(dates[0], "2025-12-21")
                self.assertEqual(dates, sorted(set(dates)))
                for row in rows:
                    date.fromisoformat(row["date"])
                    self.assertTrue(math.isfinite(row["value"]) and row["value"] > 0)
                    self.assertEqual(row["source"], "Mercatus GPU Index")
                    self.assertEqual(row["quality"], "unified_daily")
