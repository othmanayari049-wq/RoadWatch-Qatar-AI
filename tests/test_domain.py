from __future__ import annotations

import pytest
from pydantic import ValidationError

from roadwatch.domain.models import BoundingBox, DamageClass, Severity
from roadwatch.domain.severity import assess_severity


def test_bounding_box_area() -> None:
    box = BoundingBox(x1=10, y1=20, x2=60, y2=80)
    assert box.area == 3_000


def test_bounding_box_rejects_inverted_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x1=20, y1=10, x2=10, y2=30)


@pytest.mark.parametrize(
    ("damage_class", "confidence", "area_ratio", "expected"),
    [
        (DamageClass.LONGITUDINAL_CRACK, 0.25, 0.001, Severity.LOW),
        (DamageClass.ALLIGATOR_CRACK, 0.80, 0.04, Severity.MEDIUM),
        (DamageClass.POTHOLE, 0.95, 0.15, Severity.HIGH),
    ],
)
def test_severity_thresholds(
    damage_class: DamageClass,
    confidence: float,
    area_ratio: float,
    expected: Severity,
) -> None:
    result = assess_severity(damage_class, confidence, area_ratio)
    assert result.level is expected
    assert 0 <= result.score <= 100


def test_severity_clamps_invalid_numeric_inputs() -> None:
    result = assess_severity(DamageClass.POTHOLE, confidence=2.0, area_ratio=-1.0)
    assert result.score == 65.0
    assert result.level is Severity.MEDIUM
