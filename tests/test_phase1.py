from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from cloudthrift.collectors import cost_explorer, ec2_inventory
from cloudthrift.handlers import collector
from cloudthrift.reporting.report import build_costs, upload


def test_cost_pagination_and_month_boundary():
    client = Mock()
    group = {
        "Keys": ["Amazon EC2"],
        "Metrics": {"UnblendedCost": {"Amount": "1.25", "Unit": "USD"}},
    }
    day = {
        "TimePeriod": {"Start": "2026-10-31", "End": "2026-11-01"},
        "Estimated": True,
        "Groups": [group],
    }
    client.get_cost_and_usage.side_effect = [
        {"ResultsByTime": [day], "NextPageToken": "next"},
        {"ResultsByTime": []},
    ]
    raw = cost_explorer.collect(client, date(2026, 11, 1))
    assert raw["start"] == "2026-10-31"
    assert client.get_cost_and_usage.call_args.kwargs["NextPageToken"] == "next"
    summary, services = build_costs(raw, datetime(2026, 11, 1, tzinfo=UTC))
    assert summary["daily"][0]["estimated"] is True
    assert services == []


def test_empty_and_api_error():
    client = Mock()
    client.get_cost_and_usage.return_value = {}
    assert cost_explorer.collect(client, date(2026, 11, 23))["days"] == []
    client.get_cost_and_usage.side_effect = RuntimeError("unavailable")
    with pytest.raises(RuntimeError):
        cost_explorer.collect(client, date(2026, 11, 23))


def test_ec2_inventory_pagination():
    client = Mock()
    client.get_paginator.return_value.paginate.return_value = [
        {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1",
                            "State": {"Name": "running"},
                            "LaunchTime": datetime(2026, 1, 1, tzinfo=UTC),
                            "Tags": [{"Key": "aws:autoscaling:groupName", "Value": "workers"}],
                        }
                    ]
                }
            ]
        },
        {"Reservations": [{"Instances": [{"InstanceId": "i-2"}]}]},
    ]
    items = ec2_inventory.collect(client, "ap-south-1")
    assert [i["instance_id"] for i in items] == ["i-1", "i-2"]
    assert items[0]["auto_scaling_group"] == "workers"


def test_upload_failure_and_key():
    client = Mock()
    now = datetime(2026, 11, 23, tzinfo=UTC)
    assert upload(client, "bucket", {}, "request-1", now).endswith("report-request-1.json")
    client.put_object.side_effect = RuntimeError("denied")
    with pytest.raises(RuntimeError):
        upload(client, "bucket", {}, "request-1", now)


def test_handler_partial_failure_is_uploaded_then_raises(monkeypatch):
    monkeypatch.setenv("REPORT_BUCKET", "bucket")
    monkeypatch.setenv("INVENTORY_REGIONS", "ap-south-1")
    session = Mock()
    session.client.return_value.get_caller_identity.return_value = {"Account": "123"}
    monkeypatch.setattr(collector.boto3.session, "Session", lambda: session)
    monkeypatch.setattr(
        collector.cost_explorer, "collect", Mock(side_effect=RuntimeError("denied"))
    )
    monkeypatch.setattr(collector.ec2_inventory, "collect", Mock(return_value=[]))
    save = Mock(return_value="key")
    monkeypatch.setattr(collector, "upload", save)
    with pytest.raises(RuntimeError, match="incomplete"):
        collector.handler({}, SimpleNamespace(aws_request_id="test"))
    assert save.call_args.args[2]["collection_status"]["cost_explorer"]["ok"] is False


def test_handler_success(monkeypatch):
    monkeypatch.setenv("REPORT_BUCKET", "bucket")
    monkeypatch.setenv("INVENTORY_REGIONS", "ap-south-1")
    session = Mock()
    session.client.return_value.get_caller_identity.return_value = {"Account": "123"}
    monkeypatch.setattr(collector.boto3.session, "Session", lambda: session)
    monkeypatch.setattr(
        collector.cost_explorer,
        "collect",
        Mock(return_value={"start": "2026-11-01", "end_exclusive": "2026-11-23", "days": []}),
    )
    monkeypatch.setattr(collector.ec2_inventory, "collect", Mock(return_value=[]))
    monkeypatch.setattr(collector, "upload", Mock(return_value="key"))
    assert collector.handler({}, SimpleNamespace(aws_request_id="test"))["status"] == "complete"
