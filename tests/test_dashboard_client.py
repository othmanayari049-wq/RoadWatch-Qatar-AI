from __future__ import annotations

import json

import httpx
import pytest

from roadwatch.dashboard.client import DashboardAPIError, RoadWatchClient


def test_readiness_success() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"status": "ready", "version": "0.1.0", "detail": "loaded"}
        )
    )
    with RoadWatchClient("http://test", transport=transport) as client:
        ready, detail = client.readiness()
    assert ready is True
    assert detail == "loaded"


def test_readiness_handles_connection_failure() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with RoadWatchClient("http://test", transport=httpx.MockTransport(fail)) as client:
        ready, detail = client.readiness()
    assert ready is False
    assert "unavailable" in detail


def test_api_error_uses_server_detail() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"detail": "Model checkpoint not found"})
    )
    with (
        RoadWatchClient("http://test", transport=transport) as client,
        pytest.raises(DashboardAPIError, match="Model checkpoint not found"),
    ):
        client.inspections()


def test_summary_is_validated() -> None:
    payload = {
        "total_inspections": 2,
        "total_detections": 3,
        "geotagged_inspections": 1,
        "average_inference_ms": 14.2,
        "damage_class_counts": {"D00": 1, "D10": 0, "D20": 0, "D40": 2},
        "severity_counts": {"low": 1, "medium": 1, "high": 1},
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )
    )
    with RoadWatchClient("http://test", transport=transport) as client:
        summary = client.summary()
    assert summary.total_detections == 3
