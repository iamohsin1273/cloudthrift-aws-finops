"""Collect paginated EC2 inventory without logging tag values."""

from typing import Any


def collect(client: Any, region: str) -> list[dict[str, Any]]:
    instances = []
    for page in client.get_paginator("describe_instances").paginate():
        for reservation in page.get("Reservations", []):
            for item in reservation.get("Instances", []):
                tags = {tag["Key"]: tag.get("Value", "") for tag in item.get("Tags", [])}
                instances.append(
                    {
                        "instance_id": item["InstanceId"],
                        "instance_type": item.get("InstanceType"),
                        "state": item.get("State", {}).get("Name"),
                        "region": region,
                        "availability_zone": item.get("Placement", {}).get("AvailabilityZone"),
                        "launch_time": item["LaunchTime"].isoformat()
                        if item.get("LaunchTime")
                        else None,
                        "tags": tags,
                        "auto_scaling_group": tags.get("aws:autoscaling:groupName"),
                    }
                )
    return instances
