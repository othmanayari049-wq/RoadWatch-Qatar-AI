from __future__ import annotations

import pytest
from PIL import Image

from roadwatch.domain.models import DamageClass
from roadwatch.exceptions import ModelUnavailableError, UnknownDamageClassError
from roadwatch.services.detector import UnavailableDetector, normalize_damage_class


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
