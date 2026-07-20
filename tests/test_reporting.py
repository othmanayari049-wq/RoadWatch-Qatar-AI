from __future__ import annotations

from roadwatch.domain.models import (
    BoundingBox,
    DamageClass,
    Detection,
    Prediction,
    Severity,
    StoredInspection,
)
from roadwatch.services.reporting import render_html_report


def sample_prediction() -> Prediction:
    return Prediction(
        model_version="test-v1",
        image_width=1280,
        image_height=720,
        inference_ms=22.4,
        detections=(
            Detection(
                damage_class=DamageClass.POTHOLE,
                label="Pothole",
                confidence=0.91,
                bbox=BoundingBox(x1=100, y1=200, x2=300, y2=400),
                area_ratio=0.04,
                severity_score=75.0,
                severity=Severity.HIGH,
            ),
        ),
    )


def test_html_report_contains_inspection_details_and_disclaimer() -> None:
    record = StoredInspection(
        source_filename="doha-road.jpg",
        prediction=sample_prediction(),
    )
    report = render_html_report(record)
    assert "RoadWatch Qatar AI" in report
    assert str(record.prediction.id) in report
    assert "D40" in report
    assert "91.0%" in report
    assert "Decision-support only" in report


def test_html_report_escapes_untrusted_metadata() -> None:
    record = StoredInspection(
        source_filename='<script>alert("x")</script>.jpg',
        prediction=sample_prediction().model_copy(update={"model_version": "<unsafe>"}),
    )
    report = render_html_report(record)
    assert "<script>" not in report
    assert "&lt;script&gt;" in report
    assert "&lt;unsafe&gt;" in report
