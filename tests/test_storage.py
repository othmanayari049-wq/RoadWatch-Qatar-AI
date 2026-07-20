from __future__ import annotations

from roadwatch.domain.models import (
    BoundingBox,
    DamageClass,
    Detection,
    GeoPoint,
    Prediction,
    Severity,
)
from roadwatch.storage.database import Database, InspectionRepository


def sample_prediction() -> Prediction:
    return Prediction(
        model_version="roadwatch-test-v1",
        image_width=1280,
        image_height=720,
        inference_ms=22.4,
        location=GeoPoint(latitude=25.2854, longitude=51.5310),
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


def make_repository() -> InspectionRepository:
    database = Database("sqlite://")
    database.create_schema()
    return InspectionRepository(database)


def test_save_and_get_round_trip() -> None:
    repository = make_repository()
    prediction = sample_prediction()
    repository.save(prediction, "doha-road.jpg")

    stored = repository.get(prediction.id)
    assert stored is not None
    assert stored.source_filename == "doha-road.jpg"
    assert stored.prediction == prediction


def test_list_is_newest_first() -> None:
    repository = make_repository()
    first = sample_prediction()
    second = first.model_copy(update={"id": first.id.__class__(int=2)})
    repository.save(first, "first.jpg")
    repository.save(second, "second.jpg")

    records = repository.list()
    assert len(records) == 2
    assert {item.source_filename for item in records} == {"first.jpg", "second.jpg"}


def test_summary_aggregates_predictions() -> None:
    repository = make_repository()
    repository.save(sample_prediction(), "one.jpg")

    summary = repository.summary()
    assert summary.total_inspections == 1
    assert summary.total_detections == 1
    assert summary.geotagged_inspections == 1
    assert summary.damage_class_counts[DamageClass.POTHOLE] == 1
    assert summary.severity_counts[Severity.HIGH] == 1


def test_empty_summary_is_well_formed() -> None:
    summary = make_repository().summary()
    assert summary.total_inspections == 0
    assert summary.average_inference_ms == 0
    assert all(count == 0 for count in summary.damage_class_counts.values())
