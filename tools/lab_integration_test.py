"""Run safe end-to-end checks against the running SENTINEL corporate lab."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:
        document: Any = json.load(response)
    if not isinstance(document, dict):
        raise TypeError(f"Expected an object response from {url}")
    return document


def post_json(url: str) -> dict[str, Any]:
    request = Request(url, data=b"", method="POST", headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:
        document: Any = json.load(response)
    if not isinstance(document, dict):
        raise TypeError(f"Expected an object response from {url}")
    return document


def compose_exec(service: str, activity: str) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            service,
            "python",
            "/app/agent.py",
            "activity",
            activity,
        ],
        check=True,
    )


def wait_for_event(
    base_url: str,
    *,
    event_type: str,
    source: str,
    since: datetime,
    source_ip: str | None = None,
    scenario_run_id: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    parameters = {
        "event_type": event_type,
        "source": source,
        "start_time": since.isoformat(),
        "page_size": 100,
        **({"source_ip": source_ip} if source_ip else {}),
        **({"scenario_run_id": scenario_run_id} if scenario_run_id else {}),
    }
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page = get_json(f"{base_url}/api/v1/events?{urlencode(parameters)}")
        items = page.get("items")
        if isinstance(items, list) and items:
            event = items[0]
            if isinstance(event, dict):
                return event
        time.sleep(1)
    raise TimeoutError(f"No {source}/{event_type} event arrived within {timeout} seconds")


def wait_for_scenario_run(base_url: str, run_id: str, timeout: int = 60) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = get_json(f"{base_url}/api/v1/simulator/runs/{run_id}")
        if run.get("status") not in {"pending", "running"}:
            return run
        time.sleep(1)
    raise TimeoutError(f"SCN-004 did not finish within {timeout} seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the safe corporate lab telemetry path")
    parser.add_argument("--sentinel-url", default="http://127.0.0.1:8000")
    parser.add_argument("--lab-web-url", default="http://127.0.0.1:8081")
    args = parser.parse_args()
    sentinel_url = args.sentinel_url.rstrip("/")
    since = datetime.now(UTC) - timedelta(seconds=5)

    health = get_json(f"{sentinel_url}/api/v1/health")
    if health.get("status") != "healthy":
        raise RuntimeError("SENTINEL API is not healthy")

    profile = get_json(f"{args.lab_web_url.rstrip('/')}/api/profile")
    if profile.get("username") != "demo-user":
        raise RuntimeError("Corporate portal did not return the fictional demo profile")
    web_event = wait_for_event(
        sentinel_url,
        event_type="http_request",
        source="web_access",
        since=since,
    )

    compose_exec("sentinel-employee-01", "process")
    process_event = wait_for_event(
        sentinel_url,
        event_type="process_execution",
        source="linux_process",
        since=since,
        source_ip="10.10.20.10",
    )

    started_run = post_json(f"{sentinel_url}/api/v1/simulator/run/SCN-004")
    run_id = started_run.get("id")
    if not isinstance(run_id, str):
        raise TypeError("SCN-004 did not return a persistent run ID")
    scenario_run = wait_for_scenario_run(sentinel_url, run_id)
    if scenario_run.get("status") != "completed":
        raise RuntimeError(f"SCN-004 did not complete: {scenario_run.get('error_message')}")

    database_event = wait_for_event(
        sentinel_url,
        event_type="database_connection",
        source="database_client",
        source_ip="10.10.20.10",
        since=since,
        scenario_run_id=run_id,
    )
    detections = scenario_run.get("detections")
    detection = (
        next(
            (
                item
                for item in detections
                if isinstance(item, dict) and item.get("rule_id") == "DET-DB-001"
            ),
            None,
        )
        if isinstance(detections, list)
        else None
    )
    if not detection or detection.get("observed") is not True:
        raise RuntimeError("SCN-004 did not attribute an observed DET-DB-001 alert")
    alert_ids = detection.get("alert_ids")
    if not isinstance(alert_ids, list) or not alert_ids or not isinstance(alert_ids[0], str):
        raise RuntimeError("SCN-004 did not return an attributed alert ID")
    alert = get_json(f"{sentinel_url}/api/v1/alerts/{alert_ids[0]}")
    if alert.get("mitre_technique_id") is not None:
        raise RuntimeError("DET-DB-001 must remain intentionally unmapped")

    lab_status = get_json(f"{sentinel_url}/api/v1/lab/status")
    print("Corporate lab integration passed")
    print(f"web_event_id={web_event['id']}")
    print(f"process_event_id={process_event['id']}")
    print(f"scenario_run_id={run_id}")
    print(f"database_event_id={database_event['id']}")
    print(f"database_alert_id={alert['id']}")
    print(f"lab_assets_online={lab_status.get('active_assets')}/{lab_status.get('total_assets')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
