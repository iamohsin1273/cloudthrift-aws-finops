"""Cost Explorer collection; the end date is exclusive."""

from datetime import date, timedelta
from typing import Any


def collect(client: Any, today: date) -> dict[str, Any]:
    # One daily, service-grouped request provides both daily and month-to-date totals.
    # Include yesterday even on the first of the month.
    start = min(today.replace(day=1), today - timedelta(days=1))
    request = {
        "TimePeriod": {"Start": start.isoformat(), "End": today.isoformat()},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
    }
    results: dict[str, dict[str, Any]] = {}
    token = None
    while True:
        response = client.get_cost_and_usage(
            **request, **({"NextPageToken": token} if token else {})
        )
        for day in response.get("ResultsByTime", []):
            key = day["TimePeriod"]["Start"]
            entry = results.setdefault(
                key, {"period": day["TimePeriod"], "estimated": False, "groups": []}
            )
            entry["estimated"] = entry["estimated"] or day.get("Estimated", False)
            entry["groups"].extend(day.get("Groups", []))
        token = response.get("NextPageToken")
        if not token:
            break
    return {
        "start": start.isoformat(),
        "end_exclusive": today.isoformat(),
        "days": list(results.values()),
    }
