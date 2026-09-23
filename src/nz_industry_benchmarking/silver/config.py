"""Runtime configuration for Silver processing."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.bronze.config import (
    DEFAULT_BRONZE_PATH,
    DEFAULT_SPARK_MASTER,
)

DEFAULT_SILVER_PATH = Path("data/silver/aes_observations")


@dataclass(frozen=True, slots=True)
class SilverConfig:
    """Paths and Spark settings needed for a Silver run."""

    bronze_path: Path = DEFAULT_BRONZE_PATH
    silver_path: Path = DEFAULT_SILVER_PATH
    spark_master: str = DEFAULT_SPARK_MASTER
    spark_log_level: str = "WARN"

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> SilverConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        return cls(
            bronze_path=Path(values.get("BRONZE_TABLE_PATH", DEFAULT_BRONZE_PATH)),
            silver_path=Path(values.get("SILVER_TABLE_PATH", DEFAULT_SILVER_PATH)),
            spark_master=values.get("SPARK_MASTER", DEFAULT_SPARK_MASTER),
            spark_log_level=values.get("SPARK_LOG_LEVEL", "WARN"),
        )
