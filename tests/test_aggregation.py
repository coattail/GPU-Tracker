import unittest

from gpu_monitor.aggregation import aggregate_observations
from gpu_monitor.models import PriceObservation


def observation(**overrides):
    base = {
        "captured_at": "2026-05-15T00:00:00Z",
        "provider": "Example",
        "price_type": "list",
        "gpu_model": "H100",
        "region": "us-east-1",
        "instance_type": "demo",
        "gpu_count": 8,
        "price_per_instance_hour_usd": 24.0,
        "source_url": "https://example.com",
    }
    base.update(overrides)
    return PriceObservation.build(**base)


class AggregationTests(unittest.TestCase):
    def test_multi_gpu_normalization_and_list_summary(self):
        result = aggregate_observations(
            [
                observation(price_per_instance_hour_usd=24.0),
                observation(provider="Other", price_per_instance_hour_usd=40.0),
            ]
        )
        latest = result["latest"]["H100"]["list"]
        self.assertEqual(latest["min"], 3.0)
        self.assertEqual(latest["median"], 4.0)
        self.assertEqual(latest["max"], 5.0)

    def test_dynamic_summary_keeps_price_types_separate(self):
        result = aggregate_observations(
            [
                observation(price_type="spot", price_per_instance_hour_usd=8.0),
                observation(price_type="spot", provider="Other", price_per_instance_hour_usd=16.0),
                observation(price_type="marketplace", provider="Third", price_per_instance_hour_usd=24.0),
            ]
        )
        self.assertEqual(result["latest"]["H100"]["spot"]["median"], 1.5)
        self.assertEqual(result["latest"]["H100"]["marketplace"]["median"], 3.0)
        self.assertEqual(result["latest"]["H100"]["spot"]["sample_count"], 2)

    def test_duplicate_same_day_records_stay_in_details_but_aggregate_by_day(self):
        result = aggregate_observations(
            [
                observation(captured_at="2026-05-15T00:00:00Z"),
                observation(captured_at="2026-05-15T12:00:00Z", provider="Other", price_per_instance_hour_usd=32.0),
            ]
        )
        self.assertEqual(len(result["series"]["H100"]["list"]), 1)
        self.assertEqual(len(result["details"]), 2)
