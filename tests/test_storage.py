import json
import tempfile
import unittest
from pathlib import Path

from gpu_monitor.models import PriceObservation
from gpu_monitor.storage import load_observations, write_snapshot


class StorageTests(unittest.TestCase):
    def test_snapshot_dedupes_same_observation_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            obs = PriceObservation.build(
                captured_at="2026-05-15T00:00:00Z",
                provider="Example",
                price_type="list",
                gpu_model="H100",
                region="us-east-1",
                instance_type="demo",
                gpu_count=8,
                price_per_instance_hour_usd=24.0,
                source_url="https://example.com",
            )
            write_snapshot(path, [obs, obs])
            payload = json.loads(path.read_text())
            self.assertEqual(len(payload["observations"]), 1)
            self.assertEqual(len(load_observations([path])), 1)
