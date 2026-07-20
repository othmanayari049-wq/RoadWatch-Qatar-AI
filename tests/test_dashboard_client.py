from __future__ import annotations

import json

import httpx
import pytest

from roadwatch.dashboard.client import DashboardAPIError, RoadWatchClient


def inspection_payload() -> dict[str, object]:
    return {
        "source_filename": "road.jpg",
        "prediction": {
            "id": "00000000-0000-0000-0000-000000000001",
            "created_at": "2026-07-20T08:00:00Z",
            "model_version": "test-v1",
            "image_width": 100,
            "image_height": 80,
            "inference_ms": 12.5,
            "detections": [],
            "location": None,
        },
    }


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


def test_predict_sends_multipart_and_validates_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "multipart/form-data" in request.headers["content-type"]
        return httpx.Response(201, json=inspection_payload())

    with RoadWatchClient("http://test", transport=httpx.MockTransport(handler)) as client:
        result = client.predict(
            "road.jpg",
            b"image-bytes",
            "image/jpeg",
            latitude=25.28,
            longitude=51.53,
        )
    assert result.source_filename == "road.jpg"


def test_list_and_get_inspections() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/inspections"):
            return httpx.Response(200, json=[inspection_payload()])
        return httpx.Response(200, json=inspection_payload())

    with RoadWatchClient("http://test", transport=httpx.MockTransport(handler)) as client:
        records = client.inspections(limit=10)
        fetched = client.inspection(records[0].prediction.id)
    assert len(records) == 1
    assert fetched.prediction.id == records[0].prediction.id


def test_unreadable_response_is_rejected() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(502, text="gateway"))
    with (
        RoadWatchClient("http://test", transport=transport) as client,
        pytest.raises(DashboardAPIError, match="unreadable"),
    ):
        client.summary()
