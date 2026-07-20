from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from roadwatch.exceptions import InvalidImageError
from roadwatch.services.image_io import decode_image


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

