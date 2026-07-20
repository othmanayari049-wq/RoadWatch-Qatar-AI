"""Validated domain models shared by the API, detector, and dashboard."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DamageClass(StrEnum):
    """RDD2022 road-damage labels."""

    LONGITUDINAL_CRACK = "D00"
    TRANSVERSE_CRACK = "D10"
    ALLIGATOR_CRACK = "D20"
    POTHOLE = "D40"

    @property
    def display_name(self) -> str:
        return {
            self.LONGITUDINAL_CRACK: "Longitudinal crack",
            self.TRANSVERSE_CRACK: "Transverse crack",
            self.ALLIGATOR_CRACK: "Alligator crack",
            self.POTHOLE: "Pothole",
        }[self]


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


Coordinate = Annotated[float, Field(ge=0)]


class BoundingBox(BaseModel):
    """Pixel-space bounding box in ``xyxy`` format."""

    model_config = ConfigDict(frozen=True)

    x1: Coordinate
    y1: Coordinate
    x2: Coordinate
    y2: Coordinate

    @model_validator(mode="after")
    def validate_order(self) -> "BoundingBox":
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("x2/y2 must be greater than x1/y1")
        return self

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


class GeoPoint(BaseModel):
    """WGS84 coordinate attached to an optional inspection location."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Detection(BaseModel):
    """One detected road defect with transparent severity information."""

    model_config = ConfigDict(frozen=True)

    damage_class: DamageClass
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox
    area_ratio: float = Field(ge=0, le=1)
    severity_score: float = Field(ge=0, le=100)
    severity: Severity


class Prediction(BaseModel):
    """Complete inference result returned by the service."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_version: str
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    inference_ms: float = Field(ge=0)
    detections: tuple[Detection, ...] = ()
    location: GeoPoint | None = None

    @property
    def maximum_severity(self) -> Severity | None:
        if not self.detections:
            return None
        rank = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2}
        return max((item.severity for item in self.detections), key=rank.__getitem__)


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None


class StoredInspection(BaseModel):
    """Persisted prediction plus non-sensitive source metadata."""

    model_config = ConfigDict(frozen=True)

    source_filename: str
    prediction: Prediction


class AnalyticsSummary(BaseModel):
    """Portfolio and dashboard-level aggregate inspection statistics."""

    model_config = ConfigDict(frozen=True)

    total_inspections: int = Field(ge=0)
    total_detections: int = Field(ge=0)
    geotagged_inspections: int = Field(ge=0)
    average_inference_ms: float = Field(ge=0)
    damage_class_counts: dict[DamageClass, int]
    severity_counts: dict[Severity, int]
