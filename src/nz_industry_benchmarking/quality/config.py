"""Runtime configuration for Silver data-quality assessment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.bronze.config import DEFAULT_SPARK_MASTER
from nz_industry_benchmarking.silver.config import DEFAULT_SILVER_PATH

DEFAULT_QUALITY_REPORT_PATH = Path("data/quality/silver-quality-report.json")


@dataclass(frozen=True, slots=True)
class QualityConfig:
    """Paths and Spark settings for one quality assessment."""

    silver_path: Path = DEFAULT_SILVER_PATH
    report_path: Path = DEFAULT_QUALITY_REPORT_PATH
    spark_master: str = DEFAULT_SPARK_MASTER
    spark_log_level: str = "WARN"

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> QualityConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        return cls(
            silver_path=Path(values.get("SILVER_TABLE_PATH", DEFAULT_SILVER_PATH)),
            report_path=Path(
                values.get("QUALITY_REPORT_PATH", DEFAULT_QUALITY_REPORT_PATH)
            ),
            spark_master=values.get("SPARK_MASTER", DEFAULT_SPARK_MASTER),
            spark_log_level=values.get("SPARK_LOG_LEVEL", "WARN"),
        )
