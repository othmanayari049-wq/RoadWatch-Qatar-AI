"""SQLAlchemy persistence for predictions and dashboard analytics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from roadwatch.domain.models import (
    AnalyticsSummary,
    DamageClass,
    Prediction,
    Severity,
    StoredInspection,
)


class Base(DeclarativeBase):
    pass


class InspectionRecord(Base):
    """Compact query columns plus the canonical Pydantic payload as JSON."""

    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    model_version: Mapped[str] = mapped_column(String(100), index=True)
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)
    inference_ms: Mapped[float] = mapped_column(Float)
    detection_count: Mapped[int] = mapped_column(Integer, index=True)
    maximum_severity: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_json: Mapped[str] = mapped_column(Text)


class Database:
    """Engine/session lifecycle wrapper compatible with SQLite and PostgreSQL."""

    def __init__(self, url: str) -> None:
        kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
        self.engine: Engine = create_engine(url, **kwargs)
        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class InspectionRepository:
    """Repository isolating API code from SQLAlchemy details."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, prediction: Prediction, source_filename: str) -> StoredInspection:
        safe_filename = source_filename.strip()[:255] or "unnamed-image"
        maximum_severity = prediction.maximum_severity
        record = InspectionRecord(
            id=str(prediction.id),
            created_at=prediction.created_at,
            source_filename=safe_filename,
            model_version=prediction.model_version,
            image_width=prediction.image_width,
            image_height=prediction.image_height,
            inference_ms=prediction.inference_ms,
            detection_count=len(prediction.detections),
            maximum_severity=maximum_severity.value if maximum_severity else None,
            latitude=prediction.location.latitude if prediction.location else None,
            longitude=prediction.location.longitude if prediction.location else None,
            prediction_json=prediction.model_dump_json(),
        )
        with self._database.session() as session:
            session.add(record)
        return StoredInspection(source_filename=safe_filename, prediction=prediction)

    def get(self, inspection_id: UUID) -> StoredInspection | None:
        with self._database.session() as session:
            record = session.get(InspectionRecord, str(inspection_id))
            return self._to_domain(record) if record else None

    def list(self, limit: int = 50, offset: int = 0) -> list[StoredInspection]:
        statement = (
            select(InspectionRecord)
            .order_by(InspectionRecord.created_at.desc())
            .limit(min(max(limit, 1), 200))
            .offset(max(offset, 0))
        )
        with self._database.session() as session:
            records = session.scalars(statement).all()
            return [self._to_domain(record) for record in records]

    def summary(self) -> AnalyticsSummary:
        with self._database.session() as session:
            records = session.scalars(select(InspectionRecord)).all()

        predictions = [Prediction.model_validate_json(item.prediction_json) for item in records]
        class_counts: Counter[DamageClass] = Counter()
        severity_counts: Counter[Severity] = Counter()
        inference_total = 0.0
        geotagged = 0
        for prediction in predictions:
            inference_total += prediction.inference_ms
            geotagged += int(prediction.location is not None)
            class_counts.update(item.damage_class for item in prediction.detections)
            severity_counts.update(item.severity for item in prediction.detections)

        total = len(predictions)
        return AnalyticsSummary(
            total_inspections=total,
            total_detections=sum(class_counts.values()),
            geotagged_inspections=geotagged,
            average_inference_ms=round(inference_total / total, 2) if total else 0.0,
            damage_class_counts={item: class_counts[item] for item in DamageClass},
            severity_counts={item: severity_counts[item] for item in Severity},
        )

    @staticmethod
    def _to_domain(record: InspectionRecord) -> StoredInspection:
        return StoredInspection(
            source_filename=record.source_filename,
            prediction=Prediction.model_validate_json(record.prediction_json),
        )
