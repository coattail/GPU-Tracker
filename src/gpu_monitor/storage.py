from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

from .models import PriceObservation


def load_observations(paths: Iterable[Path]) -> list[PriceObservation]:
    observations: list[PriceObservation] = []
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        for row in payload.get("observations", []):
            observations.append(PriceObservation.from_dict(row))
    return observations


def write_snapshot(path: Path, observations: Iterable[PriceObservation], *, errors: list[dict] | None = None) -> None:
    deduped: OrderedDict[tuple, PriceObservation] = OrderedDict()
    for obs in observations:
        key = (
            obs.captured_at,
            obs.provider,
            obs.price_type,
            obs.gpu_model,
            obs.region,
            obs.instance_type,
        )
        deduped[key] = obs
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "observations": [obs.to_dict() for obs in deduped.values()],
                "errors": errors or [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
