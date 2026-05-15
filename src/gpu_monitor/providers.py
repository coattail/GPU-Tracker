from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests

from .models import PriceObservation
from .normalize import normalize_gpu_model

AWS_INSTANCE_MAP = {
    "p5.48xlarge": ("H100", 8),
    "p5e.48xlarge": ("H200", 8),
    "p5en.48xlarge": ("H200", 8),
    "p4de.24xlarge": ("A100 80GB", 8),
    "g6e.48xlarge": ("L40S", 8),
}

AZURE_SKU_MAP = {
    "Standard_ND96isr_H100_v5": ("H100", 8),
    "Standard_NC40ads_H100_v5": ("H100", 1),
    "Standard_NC80adis_H100_v5": ("H100", 2),
}

COREWEAVE_STATIC_ROWS = {
    "b200-8x": ("B200", 8, 68.80),
    "gd-8xh200ib-i128": ("H200", 8, 50.44),
    "gd-8xh100ib-i128": ("H100", 8, 49.24),
    "gd-8xl40s-i128": ("L40S", 8, 18.00),
    "gd-8xa100-i128": ("A100 80GB", 8, 21.60),
}


@dataclass
class CollectorResult:
    observations: list[PriceObservation]
    errors: list[dict]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(provider: str, message: str) -> dict:
    return {"provider": provider, "message": message}


def collect_coreweave(captured_at: str | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    source_url = "https://docs.coreweave.com/pricing/pricing-instances"
    observations = [
        PriceObservation.build(
            captured_at=timestamp,
            provider="CoreWeave",
            price_type="list",
            gpu_model=model,
            region="global",
            instance_type=instance_type,
            gpu_count=gpu_count,
            price_per_instance_hour_usd=price,
            source_url=source_url,
        )
        for instance_type, (model, gpu_count, price) in COREWEAVE_STATIC_ROWS.items()
    ]
    return CollectorResult(observations=observations, errors=[])


def collect_azure(captured_at: str | None = None, session: requests.Session | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    session = session or requests.Session()
    url = "https://prices.azure.com/api/retail/prices"
    params = {"$filter": "serviceName eq 'Virtual Machines'"}
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    page_count = 0
    try:
        while url and page_count < 40:
            response = session.get(url, params=params if page_count == 0 else None, timeout=30)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("Items", []):
                sku = item.get("armSkuName") or ""
                if sku not in AZURE_SKU_MAP:
                    continue
                if item.get("unitOfMeasure") != "1 Hour":
                    continue
                if item.get("type") != "Consumption":
                    continue
                sku_name = item.get("skuName") or ""
                if "Spot" in sku_name or "Low Priority" in sku_name:
                    price_type = "spot"
                else:
                    price_type = "list"
                model, gpu_count = AZURE_SKU_MAP[sku]
                observations.append(
                    PriceObservation.build(
                        captured_at=timestamp,
                        provider="Azure",
                        price_type=price_type,
                        gpu_model=model,
                        region=item.get("armRegionName") or item.get("location") or "unknown",
                        instance_type=sku,
                        gpu_count=gpu_count,
                        price_per_instance_hour_usd=float(item.get("retailPrice") or 0),
                        source_url="https://prices.azure.com/api/retail/prices",
                    )
                )
            url = payload.get("NextPageLink")
            params = None
            page_count += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(_error("Azure", str(exc)))
    return CollectorResult(observations=observations, errors=errors)


def collect_gcp(captured_at: str | None = None, session: requests.Session | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    api_key = os.getenv("GCP_API_KEY")
    if not api_key:
        return CollectorResult([], [_error("GCP", "skipped: GCP_API_KEY is not set")])
    session = session or requests.Session()
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    try:
        services = session.get(
            "https://cloudbilling.googleapis.com/v1/services",
            params={"key": api_key},
            timeout=30,
        )
        services.raise_for_status()
        service_name = next(
            service["name"]
            for service in services.json().get("services", [])
            if service.get("displayName") == "Compute Engine"
        )
        page_token = None
        while True:
            params = {"key": api_key, "pageSize": 5000}
            if page_token:
                params["pageToken"] = page_token
            response = session.get(
                f"https://cloudbilling.googleapis.com/v1/{service_name}/skus",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            for sku in payload.get("skus", []):
                description = sku.get("description") or ""
                model = normalize_gpu_model(description)
                if not model:
                    continue
                pricing_info = sku.get("pricingInfo") or []
                if not pricing_info:
                    continue
                expression = pricing_info[0].get("pricingExpression") or {}
                rates = expression.get("tieredRates") or []
                if not rates:
                    continue
                units = float(rates[0].get("unitPrice", {}).get("units", 0))
                nanos = float(rates[0].get("unitPrice", {}).get("nanos", 0)) / 1_000_000_000
                price = units + nanos
                if price <= 0:
                    continue
                for region in sku.get("serviceRegions") or ["global"]:
                    observations.append(
                        PriceObservation.build(
                            captured_at=timestamp,
                            provider="GCP",
                            price_type="list",
                            gpu_model=model,
                            region=region,
                            instance_type=sku.get("skuId") or description,
                            gpu_count=1,
                            price_per_instance_hour_usd=price,
                            source_url="https://cloudbilling.googleapis.com/v1/services",
                        )
                    )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:  # noqa: BLE001
        errors.append(_error("GCP", str(exc)))
    return CollectorResult(observations=observations, errors=errors)


def _boto3_client(service_name: str, region_name: str | None = None):
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("boto3 is required for AWS collectors") from exc
    return boto3.client(service_name, region_name=region_name)


def collect_aws_list(captured_at: str | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    try:
        pricing = _boto3_client("pricing", region_name="us-east-1")
        import json

        for instance_type, (model, gpu_count) in AWS_INSTANCE_MAP.items():
            paginator = pricing.get_paginator("get_products")
            for page in paginator.paginate(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                    {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                ],
            ):
                for raw in page.get("PriceList", []):
                    payload = json.loads(raw)
                    attributes = payload.get("product", {}).get("attributes", {})
                    terms = payload.get("terms", {}).get("OnDemand", {})
                    for term in terms.values():
                        for dimension in term.get("priceDimensions", {}).values():
                            price = float(dimension.get("pricePerUnit", {}).get("USD") or 0)
                            if price <= 0:
                                continue
                            observations.append(
                                PriceObservation.build(
                                    captured_at=timestamp,
                                    provider="AWS",
                                    price_type="list",
                                    gpu_model=model,
                                    region=attributes.get("regionCode") or attributes.get("location") or "unknown",
                                    instance_type=instance_type,
                                    gpu_count=gpu_count,
                                    price_per_instance_hour_usd=price,
                                    source_url="https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html",
                                )
                            )
    except Exception as exc:  # noqa: BLE001
        errors.append(_error("AWS list", str(exc)))
    return CollectorResult(observations=observations, errors=errors)


def collect_aws_spot(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> CollectorResult:
    end_time = end_time or datetime.now(timezone.utc)
    start_time = start_time or (end_time - timedelta(days=1))
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    try:
        ec2 = _boto3_client("ec2", region_name="us-east-1")
        paginator = ec2.get_paginator("describe_spot_price_history")
        for instance_type, (model, gpu_count) in AWS_INSTANCE_MAP.items():
            for page in paginator.paginate(
                InstanceTypes=[instance_type],
                ProductDescriptions=["Linux/UNIX"],
                StartTime=start_time,
                EndTime=end_time,
            ):
                for row in page.get("SpotPriceHistory", []):
                    observations.append(
                        PriceObservation.build(
                            captured_at=row["Timestamp"].astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                            provider="AWS",
                            price_type="spot",
                            gpu_model=model,
                            region=row.get("AvailabilityZone") or "unknown",
                            instance_type=instance_type,
                            gpu_count=gpu_count,
                            price_per_instance_hour_usd=float(row["SpotPrice"]),
                            source_url="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html",
                        )
                    )
    except Exception as exc:  # noqa: BLE001
        errors.append(_error("AWS spot", str(exc)))
    return CollectorResult(observations=observations, errors=errors)


def collect_vast(captured_at: str | None = None, session: requests.Session | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    token = os.getenv("VAST_API_KEY")
    if not token:
        return CollectorResult([], [_error("Vast.ai", "skipped: VAST_API_KEY is not set")])
    session = session or requests.Session()
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    try:
        response = session.post(
            "https://console.vast.ai/api/v0/bundles/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "limit": 500,
                "type": "ondemand",
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "rented": {"eq": False},
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        offers = payload.get("offers") or []
        if isinstance(offers, dict):
            offers = [offers]
        for offer in offers:
            model = normalize_gpu_model(offer.get("gpu_name"))
            gpu_count = int(offer.get("num_gpus") or len(offer.get("gpu_ids") or []) or 0)
            price = float(offer.get("dph_total") or 0)
            if not model or gpu_count <= 0 or price <= 0:
                continue
            observations.append(
                PriceObservation.build(
                    captured_at=timestamp,
                    provider="Vast.ai",
                    price_type="marketplace",
                    gpu_model=model,
                    region=offer.get("geolocation") or "unknown",
                    instance_type=str(offer.get("id") or offer.get("bundle_id") or "offer"),
                    gpu_count=gpu_count,
                    price_per_instance_hour_usd=price,
                    source_url="https://docs.vast.ai/api-reference/search/search-offers",
                )
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(_error("Vast.ai", str(exc)))
    return CollectorResult(observations=observations, errors=errors)


def collect_all(captured_at: str | None = None) -> CollectorResult:
    timestamp = captured_at or utc_now_iso()
    results: Iterable[CollectorResult] = (
        collect_coreweave(timestamp),
        collect_azure(timestamp),
        collect_gcp(timestamp),
        collect_aws_list(timestamp),
        collect_aws_spot(start_time=datetime.now(timezone.utc) - timedelta(days=1)),
        collect_vast(timestamp),
    )
    observations: list[PriceObservation] = []
    errors: list[dict] = []
    for result in results:
        observations.extend(result.observations)
        errors.extend(result.errors)
    return CollectorResult(observations=observations, errors=errors)
