"""Secure image decoding and deterministic annotation utilities."""

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from roadwatch.domain.models import Prediction, Severity
from roadwatch.exceptions import InvalidImageError

SUPPORTED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_IMAGE_PIXELS = 40_000_000


def decode_image(data: bytes, content_type: str | None, max_bytes: int) -> Image.Image:
    """Validate and decode an uploaded image without trusting its file extension."""

    if content_type not in SUPPORTED_CONTENT_TYPES:
        accepted = ", ".join(sorted(SUPPORTED_CONTENT_TYPES))
        raise InvalidImageError(f"Unsupported content type. Accepted types: {accepted}")
    if not data:
        raise InvalidImageError("The uploaded image is empty")
    if len(data) > max_bytes:
        raise InvalidImageError(f"Image exceeds the {max_bytes // (1024 * 1024)} MB limit")

    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(BytesIO(data)) as source:
            source.verify()
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("The upload is not a valid JPEG, PNG, or WebP image") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit
    return image


def encode_jpeg(image: Image.Image, quality: int = 90) -> bytes:
    """Encode an RGB image for API streaming."""

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def annotate_image(image: Image.Image, prediction: Prediction) -> Image.Image:
    """Render detections on a copy of an image using severity-aware colors."""

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()
    colors = {
        Severity.LOW: "#16A34A",
        Severity.MEDIUM: "#F59E0B",
        Severity.HIGH: "#DC2626",
    }

    for detection in prediction.detections:
        box = detection.bbox
        color = colors[detection.severity]
        coordinates = (box.x1, box.y1, box.x2, box.y2)
        draw.rectangle(coordinates, outline=color, width=4)
        caption = (
            f"{detection.damage_class.value} {detection.confidence:.0%} "
            f"| {detection.severity.value.upper()}"
        )
        left, top, right, bottom = draw.textbbox((box.x1, box.y1), caption, font=font)
        text_height = bottom - top
        label_top = max(0.0, box.y1 - text_height - 8)
        draw.rectangle(
            (left - 3, label_top, right + 4, label_top + text_height + 7),
            fill=color,
        )
        draw.text((box.x1, label_top + 3), caption, fill="white", font=font)
    return annotated
