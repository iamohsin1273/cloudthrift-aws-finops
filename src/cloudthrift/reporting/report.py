"""Versioned report construction and deterministic S3 uploads."""

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any


def build_costs(raw: dict[str, Any], now: datetime) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daily = []
    services: dict[tuple[str, str], Decimal] = {}
    month = now.date().replace(day=1).isoformat()
    for day in raw["days"]:
        totals: dict[str, Decimal] = {}
        for group in day["groups"]:
            amount = group["Metrics"]["UnblendedCost"]
            unit = amount["Unit"]
            value = Decimal(amount["Amount"])
            totals[unit] = totals.get(unit, Decimal(0)) + value
            if day["period"]["Start"] >= month:
                key = (group["Keys"][0], unit)
                services[key] = services.get(key, Decimal(0)) + value
        daily.append(
            {
                "period": day["period"],
                "estimated": day["estimated"],
                "totals": [{"amount": str(v), "currency": k} for k, v in sorted(totals.items())],
            }
        )
    service_costs = [
        {"service": k[0], "currency": k[1], "amount": str(v)} for k, v in sorted(services.items())
    ]
    monthly: dict[str, Decimal] = {}
    for item in service_costs:
        monthly[item["currency"]] = monthly.get(item["currency"], Decimal(0)) + Decimal(
            item["amount"]
        )
    return (
        {
            "period": {"start": raw["start"], "end_exclusive": raw["end_exclusive"]},
            "daily": daily,
            "month_to_date": [
                {"currency": k, "amount": str(v)} for k, v in sorted(monthly.items())
            ],
        },
        service_costs,
    )


def upload(client: Any, bucket: str, report: dict[str, Any], request_id: str, now: datetime) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
        raise ValueError("Invalid request ID")
    key = f"reports/year={now:%Y}/month={now:%m}/day={now:%d}/report-{request_id}.json"
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(report, sort_keys=True).encode(),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    return key
