"""Runtime configuration for the read-only API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig


@dataclass(frozen=True, slots=True)
class ApiConfig:
    """API server and analytical repository settings."""

    benchmark: BenchmarkConfig
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> ApiConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        return cls(
            benchmark=BenchmarkConfig.from_environment(values),
            host=values.get("API_HOST", "127.0.0.1"),
            port=int(values.get("API_PORT", "8000")),
            log_level=values.get("API_LOG_LEVEL", "INFO"),
            cors_origins=tuple(
                origin.strip()
                for origin in values.get(
                    "API_CORS_ORIGINS",
                    "http://127.0.0.1:5173,http://localhost:5173",
                ).split(",")
                if origin.strip()
            ),
        )
