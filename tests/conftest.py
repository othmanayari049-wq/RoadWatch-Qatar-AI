from __future__ import annotations

from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from roadwatch.api.app import create_app
from roadwatch.config import Settings
from roadwatch.domain.models import (
    BoundingBox,
    DamageClass,
    Detection,
    GeoPoint,
    Prediction,
    Severity,
)
from roadwatch.storage.database import Database, InspectionRepository


class FakeDetector:
    @property
    def ready(self) -> bool:
        return True

    @property
    def model_version(self) -> str:
        return "fake-roadwatch-v1"

    @property
    def status_detail(self) -> str:
        return "Test detector ready"

    def predict(self, image: Image.Image, location: GeoPoint | None = None) -> Prediction:
        started = perf_counter()
        detection = Detection(
            damage_class=DamageClass.POTHOLE,
            label="Pothole",
            confidence=0.92,
            bbox=BoundingBox(x1=1, y1=1, x2=image.width / 2, y2=image.height / 2),
            area_ratio=0.24,
            severity_score=89.0,
            severity=Severity.HIGH,
        )
        return Prediction(
            model_version=self.model_version,
            image_width=image.width,
            image_height=image.height,
            inference_ms=(perf_counter() - started) * 1_000,
            detections=(detection,),
            location=location,
        )


@pytest.fixture
def client() -> TestClient:
    database = Database("sqlite://")
    database.create_schema()
    repository = InspectionRepository(database)
    settings = Settings(environment="test", max_upload_mb=1)
    app = create_app(settings=settings, detector=FakeDetector(), repository=repository)
    with TestClient(app) as test_client:
        yield test_client
