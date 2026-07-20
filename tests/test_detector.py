from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from PIL import Image

from roadwatch.domain.models import DamageClass
from roadwatch.exceptions import ModelUnavailableError, UnknownDamageClassError
from roadwatch.services.detector import (
    UltralyticsDetector,
    UnavailableDetector,
    build_detector,
    normalize_damage_class,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("D00", DamageClass.LONGITUDINAL_CRACK),
        ("transverse-crack", DamageClass.TRANSVERSE_CRACK),
        ("Alligator crack", DamageClass.ALLIGATOR_CRACK),
        ("pothole", DamageClass.POTHOLE),
    ],
)
def test_normalize_damage_class(label: str, expected: DamageClass) -> None:
    assert normalize_damage_class(label) is expected


def test_unknown_damage_class_is_rejected() -> None:
    with pytest.raises(UnknownDamageClassError, match="D99"):
        normalize_damage_class("D99")


def test_unavailable_detector_is_explicit() -> None:
    detector = UnavailableDetector("weights missing")
    assert detector.ready is False
    assert detector.status_detail == "weights missing"
    with pytest.raises(ModelUnavailableError, match="weights missing"):
        detector.predict(Image.new("RGB", (8, 8)))


class FakeTensor:
    def __init__(self, value: list[object]) -> None:
        self.value = value

    def cpu(self) -> FakeTensor:
        return self

    def tolist(self) -> list[object]:
        return self.value


class FakeYOLOModel:
    names: ClassVar[dict[int, str]] = {0: "D40"}

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    def predict(self, **kwargs: object) -> list[SimpleNamespace]:
        boxes = SimpleNamespace(
            xyxy=FakeTensor([[10, 20, 60, 70]]),
            conf=FakeTensor([0.93]),
            cls=FakeTensor([0]),
        )
        return [SimpleNamespace(names=self.names, boxes=boxes)]


def test_ultralytics_adapter_converts_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "roadwatch-v1.pt"
    checkpoint.write_bytes(b"test-checkpoint")
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLOModel))

    detector = UltralyticsDetector(checkpoint, device="cpu", confidence=0.4, iou=0.5)
    prediction = detector.predict(Image.new("RGB", (100, 100)))

    assert detector.ready is True
    assert detector.model_version == "roadwatch-v1"
    assert "cpu" in detector.status_detail
    assert prediction.model_version == "roadwatch-v1"
    assert prediction.detections[0].damage_class is DamageClass.POTHOLE
    assert prediction.detections[0].confidence == pytest.approx(0.93)


def test_build_detector_reports_missing_checkpoint(tmp_path: Path) -> None:
    detector = build_detector(tmp_path / "missing.pt", "cpu", 0.3, 0.5)
    assert detector.ready is False
    assert "not found" in detector.status_detail
