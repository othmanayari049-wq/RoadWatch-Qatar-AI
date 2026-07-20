from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image


def image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 80), color="gray").save(buffer, "JPEG")
    return buffer.getvalue()


def test_liveness_and_readiness(client: TestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert "X-Request-ID" in ready.headers


def test_prediction_is_persisted_and_retrievable(client: TestClient) -> None:
    created = client.post(
        "/api/v1/predictions",
        files={"image": ("road.jpg", image_bytes(), "image/jpeg")},
        data={"latitude": "25.2854", "longitude": "51.5310", "persist": "true"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["source_filename"] == "road.jpg"
    assert body["prediction"]["detections"][0]["damage_class"] == "D40"
    assert body["prediction"]["location"]["latitude"] == 25.2854

    fetched = client.get(f"/api/v1/inspections/{body['prediction']['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body

    report = client.get(f"/api/v1/inspections/{body['prediction']['id']}/report")
    assert report.status_code == 200
    assert "text/html" in report.headers["content-type"]
    assert "attachment" in report.headers["content-disposition"]
    assert "RoadWatch Qatar AI" in report.text


def test_prediction_can_skip_persistence(client: TestClient) -> None:
    created = client.post(
        "/api/v1/predictions",
        files={"image": ("private.png", image_bytes(), "image/png")},
        data={"persist": "false"},
    )
    assert created.status_code == 201
    assert client.get("/api/v1/inspections").json() == []


def test_coordinate_pair_is_required(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predictions",
        files={"image": ("road.jpg", image_bytes(), "image/jpeg")},
        data={"latitude": "25.28"},
    )
    assert response.status_code == 422


def test_invalid_image_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predictions",
        files={"image": ("road.jpg", b"invalid", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "not a valid" in response.json()["detail"]


def test_missing_inspection_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/inspections/{uuid4()}")
    assert response.status_code == 404


def test_analytics_and_prometheus_metrics(client: TestClient) -> None:
    client.get("/health/live")
    summary = client.get("/api/v1/analytics/summary")
    metrics = client.get("/metrics")
    assert summary.status_code == 200
    assert summary.json()["total_inspections"] == 0
    assert metrics.status_code == 200
    assert "roadwatch_http_requests_total" in metrics.text
