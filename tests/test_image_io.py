from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from roadwatch.domain.models import (
    BoundingBox,
    DamageClass,
    Detection,
    Prediction,
    Severity,
)
from roadwatch.exceptions import InvalidImageError
from roadwatch.services.image_io import annotate_image, decode_image, encode_jpeg


def make_image_bytes(image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 32), color=(40, 50, 60)).save(buffer, image_format)
    return buffer.getvalue()


def test_decode_valid_png() -> None:
    image = decode_image(make_image_bytes(), "image/png", max_bytes=1_000_000)
    assert image.mode == "RGB"
    assert image.size == (64, 32)


def test_decode_rejects_content_type() -> None:
    with pytest.raises(InvalidImageError, match="Unsupported content type"):
        decode_image(make_image_bytes(), "image/gif", max_bytes=1_000_000)


def test_decode_rejects_oversized_payload() -> None:
    with pytest.raises(InvalidImageError, match="exceeds"):
        decode_image(make_image_bytes(), "image/png", max_bytes=10)


def test_decode_rejects_malformed_bytes() -> None:
    with pytest.raises(InvalidImageError, match="not a valid"):
        decode_image(b"not-an-image", "image/jpeg", max_bytes=1_000_000)


def test_decode_rejects_empty_payload() -> None:
    with pytest.raises(InvalidImageError, match="empty"):
        decode_image(b"", "image/jpeg", max_bytes=1_000_000)


def test_encode_and_annotate_image() -> None:
    source = Image.new("RGB", (100, 80), color="gray")
    detection = Detection(
        damage_class=DamageClass.POTHOLE,
        label="Pothole",
        confidence=0.9,
        bbox=BoundingBox(x1=10, y1=10, x2=70, y2=60),
        area_ratio=0.2,
        severity_score=80,
        severity=Severity.HIGH,
    )
    prediction = Prediction(
        model_version="test",
        image_width=100,
        image_height=80,
        inference_ms=1,
        detections=(detection,),
    )
    annotated = annotate_image(source, prediction)
    encoded = encode_jpeg(annotated)
    assert annotated is not source
    assert annotated.getpixel((10, 10)) != source.getpixel((10, 10))
    assert encoded.startswith(b"\xff\xd8")
