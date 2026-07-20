"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ROADWATCH_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RoadWatch Qatar AI"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./roadwatch.db"
    model_path: Path = Path("models/best.pt")
    model_device: str = "cpu"
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_upload_mb: int = Field(default=15, ge=1, le=100)
    cors_origins: list[str] = ["http://localhost:8501"]

    @property
    def max_upload_bytes(self) -> int:
        """Maximum accepted upload size in bytes."""

        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""

    return Settings()

