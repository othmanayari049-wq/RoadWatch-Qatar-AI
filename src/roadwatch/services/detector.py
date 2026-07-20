"""Detector abstraction and Ultralytics implementation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, runtime_checkable

import numpy as np
from PIL import Image

from roadwatch.domain.models import (
    BoundingBox,
    DamageClass,
    Detection,
    GeoPoint,
    Prediction,
)
from roadwatch.domain.severity import assess_severity
from roadwatch.exceptions import ModelUnavailableError, UnknownDamageClassError


@runtime_checkable
class Detector(Protocol):
    """Inference contract used by the API and test doubles."""

    @property
    def ready(self) -> bool: ...

    @property
    def model_version(self) -> str: ...

    @property
    def status_detail(self) -> str: ...

    def predict(self, image: Image.Image, location: GeoPoint | None = None) -> Prediction: ...


class UnavailableDetector:
    """Explicit failure object used until trained weights are configured."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    @property
    def ready(self) -> bool:
        return False

    @property
    def model_version(self) -> str:
        return "unavailable"

    @property
    def status_detail(self) -> str:
        return self._reason

    def predict(self, image: Image.Image, location: GeoPoint | None = None) -> Prediction:
        del image, location
        raise ModelUnavailableError(self._reason)


class UltralyticsDetector:
    """Adapter around an Ultralytics road-damage object-detection checkpoint."""

    def __init__(
        self,
        model_path: Path,
        device: str = "cpu",
        confidence: float = 0.35,
        iou: float = 0.45,
    ) -> None:
        if not model_path.is_file():
            raise ModelUnavailableError(f"Model checkpoint not found: {model_path}")
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ModelUnavailableError(
                "Ultralytics is not installed; install the project with the 'ml' extra"
            ) from exc

        self._model: Any = YOLO(str(model_path))
        self._path = model_path
        self._device = device
        self._confidence = confidence
        self._iou = iou

    @property
    def ready(self) -> bool:
        return True

    @property
    def model_version(self) -> str:
        return self._path.stem

    @property
    def status_detail(self) -> str:
        return f"Loaded {self._path.name} on {self._device}"

    def predict(self, image: Image.Image, location: GeoPoint | None = None) -> Prediction:
        started = perf_counter()
        result = self._model.predict(
            source=np.asarray(image),
            conf=self._confidence,
            iou=self._iou,
            device=self._device,
            verbose=False,
        )[0]
        names: Mapping[int, str] = result.names
        detections: list[Detection] = []
        image_area = image.width * image.height

        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().tolist()
            confidences = result.boxes.conf.cpu().tolist()
            class_ids = result.boxes.cls.cpu().tolist()
            for raw_box, confidence, class_id in zip(
                boxes, confidences, class_ids, strict=True
            ):
                damage_class = normalize_damage_class(names[int(class_id)])
                box = BoundingBox(
                    x1=float(raw_box[0]),
                    y1=float(raw_box[1]),
                    x2=float(raw_box[2]),
                    y2=float(raw_box[3]),
                )
                area_ratio = min(box.area / image_area, 1.0)
                assessment = assess_severity(damage_class, float(confidence), area_ratio)
                detections.append(
                    Detection(
                        damage_class=damage_class,
                        label=damage_class.display_name,
                        confidence=float(confidence),
                        bbox=box,
                        area_ratio=area_ratio,
                        severity_score=assessment.score,
                        severity=assessment.level,
                    )
                )

        elapsed_ms = (perf_counter() - started) * 1_000
        return Prediction(
            model_version=self.model_version,
            image_width=image.width,
            image_height=image.height,
            inference_ms=elapsed_ms,
            detections=tuple(detections),
            location=location,
        )


ALIASES: dict[str, DamageClass] = {
    "d00": DamageClass.LONGITUDINAL_CRACK,
    "longitudinal_crack": DamageClass.LONGITUDINAL_CRACK,
    "longitudinal crack": DamageClass.LONGITUDINAL_CRACK,
    "d10": DamageClass.TRANSVERSE_CRACK,
    "transverse_crack": DamageClass.TRANSVERSE_CRACK,
    "transverse crack": DamageClass.TRANSVERSE_CRACK,
    "d20": DamageClass.ALLIGATOR_CRACK,
    "alligator_crack": DamageClass.ALLIGATOR_CRACK,
    "alligator crack": DamageClass.ALLIGATOR_CRACK,
    "d40": DamageClass.POTHOLE,
    "pothole": DamageClass.POTHOLE,
}


def normalize_damage_class(raw_label: str) -> DamageClass:
    """Map common checkpoint labels to canonical RDD2022 class codes."""

    key = raw_label.strip().lower().replace("-", "_")
    try:
        return ALIASES[key]
    except KeyError as exc:
        supported = ", ".join(item.value for item in DamageClass)
        raise UnknownDamageClassError(
            f"Unsupported model class '{raw_label}'. Expected one of: {supported}"
        ) from exc


def build_detector(
    model_path: Path,
    device: str,
    confidence: float,
    iou: float,
) -> Detector:
    """Build a detector while keeping service startup observable and non-crashing."""

    try:
        return UltralyticsDetector(model_path, device, confidence, iou)
    except ModelUnavailableError as exc:
        return UnavailableDetector(str(exc))
