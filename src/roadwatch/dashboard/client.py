"""Small typed client used by the Streamlit interface."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self
from uuid import UUID

import httpx

from roadwatch.domain.models import AnalyticsSummary, StoredInspection


class DashboardAPIError(RuntimeError):
    """User-displayable API failure without leaking response internals."""


class RoadWatchClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def readiness(self) -> tuple[bool, str]:
        try:
            response = self._client.get("/health/ready")
            payload = response.json()
            return response.is_success, str(payload.get("detail") or payload.get("status"))
        except (httpx.HTTPError, ValueError) as exc:
            return False, f"API unavailable: {exc}"

    def predict(
        self,
        filename: str,
        data: bytes,
        content_type: str,
        latitude: float | None = None,
        longitude: float | None = None,
        persist: bool = True,
    ) -> StoredInspection:
        form: dict[str, str] = {"persist": str(persist).lower()}
        if latitude is not None and longitude is not None:
            form.update({"latitude": str(latitude), "longitude": str(longitude)})
        response = self._client.post(
            "/api/v1/predictions",
            files={"image": (filename, data, content_type)},
            data=form,
        )
        payload = self._json_or_error(response)
        return StoredInspection.model_validate(payload)

    def inspections(self, limit: int = 200) -> list[StoredInspection]:
        response = self._client.get("/api/v1/inspections", params={"limit": limit})
        payload = self._json_or_error(response)
        return [StoredInspection.model_validate(item) for item in payload]

    def inspection(self, inspection_id: UUID) -> StoredInspection:
        response = self._client.get(f"/api/v1/inspections/{inspection_id}")
        return StoredInspection.model_validate(self._json_or_error(response))

    def summary(self) -> AnalyticsSummary:
        response = self._client.get("/api/v1/analytics/summary")
        return AnalyticsSummary.model_validate(self._json_or_error(response))

    @staticmethod
    def _json_or_error(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise DashboardAPIError(
                f"API returned an unreadable response ({response.status_code})"
            ) from exc
        if not response.is_success:
            detail = (
                payload.get("detail", "Request failed") if isinstance(payload, dict) else payload
            )
            raise DashboardAPIError(f"{response.status_code}: {detail}")
        return payload
