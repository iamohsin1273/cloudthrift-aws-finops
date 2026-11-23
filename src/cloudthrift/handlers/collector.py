"""Collector orchestration. Partial results are persisted and then reported as failure."""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.config import Config

from cloudthrift.collectors import cost_explorer, ec2_inventory
from cloudthrift.reporting.report import build_costs, upload

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
RETRIES = Config(retries={"max_attempts": 5, "mode": "standard"})


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    regions = list(
        dict.fromkeys(r.strip() for r in os.environ["INVENTORY_REGIONS"].split(",") if r.strip())
    )
    if not regions:
        raise ValueError("At least one inventory region is required")
    session = boto3.session.Session()
    account = session.client("sts", config=RETRIES).get_caller_identity()["Account"]
    status: dict[str, Any] = {}
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "project": "CloudThrift",
        "generated_at": now.isoformat(),
        "account_id": account,
        "billing_scope": "caller account Cost Explorer scope",
        "inventory_regions": regions,
        "cost_summary": None,
        "service_costs": [],
        "ec2_inventory": [],
        "collection_status": status,
    }
    try:
        raw = cost_explorer.collect(
            session.client("ce", region_name="us-east-1", config=RETRIES), now.date()
        )
        report["cost_summary"], report["service_costs"] = build_costs(raw, now)
        status["cost_explorer"] = {"ok": True}
    except Exception as exc:
        status["cost_explorer"] = {"ok": False, "error_type": type(exc).__name__}
    for region in regions:
        try:
            report["ec2_inventory"].extend(
                ec2_inventory.collect(
                    session.client("ec2", region_name=region, config=RETRIES), region
                )
            )
            status[f"ec2:{region}"] = {"ok": True}
        except Exception as exc:
            status[f"ec2:{region}"] = {"ok": False, "error_type": type(exc).__name__}
    # Scheduler supplies a stable scheduled time; retries overwrite the same object.
    scheduled = event.get("scheduled_time")
    partition_time = datetime.fromisoformat(scheduled.replace("Z", "+00:00")) if scheduled else now
    request_id = (
        hashlib.sha256(scheduled.encode()).hexdigest() if scheduled else context.aws_request_id
    )
    key = upload(
        session.client("s3", config=RETRIES),
        os.environ["REPORT_BUCKET"],
        report,
        request_id,
        partition_time,
    )
    LOG.info(json.dumps({"event": "report_uploaded", "key": key, "status": status}))
    if not all(item["ok"] for item in status.values()):
        raise RuntimeError("Collection incomplete; see report and structured log")
    return {"status": "complete", "key": key}
