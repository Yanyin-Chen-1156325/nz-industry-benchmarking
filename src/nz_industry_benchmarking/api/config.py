"""Runtime configuration for the read-only API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from nz_industry_benchmarking.api.databricks_repository import DatabricksSqlConfig
from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig


class AnalyticsBackend(StrEnum):
    """Supported analytical storage implementations."""

    LOCAL_SPARK = "local-spark"
    DATABRICKS_SQL = "databricks-sql"


@dataclass(frozen=True, slots=True)
class ApiConfig:
    """API server and analytical repository settings."""

    benchmark: BenchmarkConfig
    analytics_backend: AnalyticsBackend = AnalyticsBackend.LOCAL_SPARK
    databricks_sql: DatabricksSqlConfig | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )

    def __post_init__(self) -> None:
        if (
            self.analytics_backend is AnalyticsBackend.DATABRICKS_SQL
            and self.databricks_sql is None
        ):
            raise ValueError(
                "Databricks SQL configuration is required when "
                "NZIB_ANALYTICS_BACKEND=databricks-sql."
            )

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> ApiConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        backend_value = values.get("NZIB_ANALYTICS_BACKEND", "local-spark")
        try:
            backend = AnalyticsBackend(backend_value)
        except ValueError:
            raise ValueError(
                "NZIB_ANALYTICS_BACKEND must be 'local-spark' or 'databricks-sql'."
            ) from None
        databricks_sql = (
            DatabricksSqlConfig.from_environment(values)
            if backend is AnalyticsBackend.DATABRICKS_SQL
            else None
        )
        return cls(
            benchmark=BenchmarkConfig.from_environment(values),
            analytics_backend=backend,
            databricks_sql=databricks_sql,
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
