"""FastAPI application factory and versioned HTTP routes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram
from prometheus_client.exposition import generate_latest
from pydantic import BaseModel

from roadwatch import __version__
from roadwatch.config import Settings, get_settings
from roadwatch.domain.models import (
    AnalyticsSummary,
    ErrorResponse,
    GeoPoint,
    StoredInspection,
)
from roadwatch.exceptions import ModelUnavailableError, RoadWatchError
from roadwatch.services.detector import Detector, build_detector
from roadwatch.services.image_io import decode_image
from roadwatch.services.reporting import render_html_report
from roadwatch.storage.database import Database, InspectionRepository


class HealthResponse(BaseModel):
    status: str
    version: str
    detail: str | None = None


class Metrics:
    """Isolated Prometheus registry so multiple test apps remain deterministic."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "roadwatch_http_requests_total",
            "Total HTTP requests",
            ("method", "path", "status"),
            registry=self.registry,
        )
        self.request_duration = Histogram(
            "roadwatch_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ("method", "path"),
            registry=self.registry,
        )
        self.predictions = Counter(
            "roadwatch_predictions_total",
            "Successful model predictions",
            registry=self.registry,
        )


def create_app(
    settings: Settings | None = None,
    detector: Detector | None = None,
    repository: InspectionRepository | None = None,
) -> FastAPI:
    """Create an application with injectable adapters for testing and deployment."""

    active_settings = settings or get_settings()
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if repository is None:
            database = Database(active_settings.database_url)
            database.create_schema()
            app.state.repository = InspectionRepository(database)
        else:
            app.state.repository = repository

        app.state.detector = detector or build_detector(
            model_path=active_settings.model_path,
            device=active_settings.model_device,
            confidence=active_settings.confidence_threshold,
            iou=active_settings.iou_threshold,
        )
        yield

    app = FastAPI(
        title=active_settings.app_name,
        version=__version__,
        description=(
            "Road-damage detection and geospatial inspection API. Detection severity is "
            "an inspection-priority heuristic, not a pavement engineering assessment."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.metrics = metrics
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    MiddlewareCallable = Callable[[Request], Awaitable[Response]]

    @app.middleware("http")
    async def request_context(request: Request, call_next: MiddlewareCallable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:64]
        started = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - started
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        metrics.requests.labels(request.method, path, str(response.status_code)).inc()
        metrics.request_duration.labels(request.method, path).observe(elapsed)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RoadWatchError)
    async def roadwatch_error_handler(request: Request, exc: RoadWatchError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if isinstance(exc, ModelUnavailableError)
            else status.HTTP_400_BAD_REQUEST
        )
        payload = ErrorResponse(detail=str(exc), request_id=request_id)
        return JSONResponse(status_code=code, content=payload.model_dump(mode="json"))

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
        tags=["health"],
    )
    async def ready(request: Request, response: Response) -> HealthResponse:
        current_detector: Detector = request.app.state.detector
        if not current_detector.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(
                status="not_ready",
                version=__version__,
                detail=current_detector.status_detail,
            )
        return HealthResponse(
            status="ready",
            version=__version__,
            detail=current_detector.status_detail,
        )

    @app.post(
        "/api/v1/predictions",
        response_model=StoredInspection,
        status_code=status.HTTP_201_CREATED,
        responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
        tags=["predictions"],
    )
    async def create_prediction(
        request: Request,
        image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP road image")],
        latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
        longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
        persist: Annotated[bool, Form()] = True,
    ) -> StoredInspection:
        if (latitude is None) != (longitude is None):
            raise HTTPException(
                status_code=422,
                detail="Latitude and longitude must be supplied together",
            )
        location = (
            GeoPoint(latitude=latitude, longitude=longitude)
            if latitude is not None and longitude is not None
            else None
        )
        payload = await image.read(active_settings.max_upload_bytes + 1)
        decoded = decode_image(payload, image.content_type, active_settings.max_upload_bytes)
        current_detector: Detector = request.app.state.detector
        prediction = await run_in_threadpool(current_detector.predict, decoded, location)
        metrics.predictions.inc()

        filename = image.filename or "uploaded-road-image"
        if persist:
            current_repository: InspectionRepository = request.app.state.repository
            return await run_in_threadpool(current_repository.save, prediction, filename)
        return StoredInspection(source_filename=filename[:255], prediction=prediction)

    @app.get(
        "/api/v1/inspections",
        response_model=list[StoredInspection],
        tags=["inspections"],
    )
    async def list_inspections(
        request: Request,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StoredInspection]:
        if not 1 <= limit <= 200 or offset < 0:
            raise HTTPException(status_code=422, detail="Invalid pagination values")
        current_repository: InspectionRepository = request.app.state.repository
        return await run_in_threadpool(current_repository.list, limit, offset)

    @app.get(
        "/api/v1/inspections/{inspection_id}",
        response_model=StoredInspection,
        tags=["inspections"],
    )
    async def get_inspection(request: Request, inspection_id: UUID) -> StoredInspection:
        current_repository: InspectionRepository = request.app.state.repository
        result = await run_in_threadpool(current_repository.get, inspection_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Inspection not found")
        return result

    @app.get(
        "/api/v1/inspections/{inspection_id}/report",
        response_class=HTMLResponse,
        tags=["inspections"],
    )
    async def inspection_report(request: Request, inspection_id: UUID) -> HTMLResponse:
        current_repository: InspectionRepository = request.app.state.repository
        result = await run_in_threadpool(current_repository.get, inspection_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Inspection not found")
        return HTMLResponse(
            content=render_html_report(result),
            headers={
                "Content-Disposition": f'attachment; filename="roadwatch-{inspection_id}.html"'
            },
        )

    @app.get(
        "/api/v1/analytics/summary",
        response_model=AnalyticsSummary,
        tags=["analytics"],
    )
    async def analytics_summary(request: Request) -> AnalyticsSummary:
        current_repository: InspectionRepository = request.app.state.repository
        return await run_in_threadpool(current_repository.summary)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(
            content=generate_latest(metrics.registry),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


app = create_app()
