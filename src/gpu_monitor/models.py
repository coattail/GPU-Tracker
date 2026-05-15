from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

PriceType = Literal["list", "spot", "marketplace"]


@dataclass(frozen=True)
class PriceObservation:
    captured_at: str
    provider: str
    price_type: PriceType
    gpu_model: str
    region: str
    instance_type: str
    gpu_count: int
    price_per_instance_hour_usd: float
    price_per_gpu_hour_usd: float
    source_url: str

    def __post_init__(self) -> None:
        datetime.fromisoformat(self.captured_at.replace("Z", "+00:00"))
        if self.price_type not in {"list", "spot", "marketplace"}:
            raise ValueError(f"unsupported price_type: {self.price_type}")
        if self.gpu_count <= 0:
            raise ValueError("gpu_count must be positive")
        if self.price_per_instance_hour_usd < 0:
            raise ValueError("price_per_instance_hour_usd must be non-negative")
        if self.price_per_gpu_hour_usd < 0:
            raise ValueError("price_per_gpu_hour_usd must be non-negative")

    @classmethod
    def build(
        cls,
        *,
        captured_at: str,
        provider: str,
        price_type: PriceType,
        gpu_model: str,
        region: str,
        instance_type: str,
        gpu_count: int,
        price_per_instance_hour_usd: float,
        source_url: str,
    ) -> "PriceObservation":
        return cls(
            captured_at=captured_at,
            provider=provider,
            price_type=price_type,
            gpu_model=gpu_model,
            region=region,
            instance_type=instance_type,
            gpu_count=gpu_count,
            price_per_instance_hour_usd=round(float(price_per_instance_hour_usd), 6),
            price_per_gpu_hour_usd=round(float(price_per_instance_hour_usd) / gpu_count, 6),
            source_url=source_url,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PriceObservation":
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
