"""Runtime configuration for Gold metric processing."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.bronze.config import DEFAULT_SPARK_MASTER
from nz_industry_benchmarking.silver.config import DEFAULT_SILVER_PATH

DEFAULT_GOLD_METRICS_PATH = Path("data/gold/industry_financial_metrics")


@dataclass(frozen=True, slots=True)
class GoldConfig:
    """Paths and Spark settings for one Gold processing run."""

    silver_path: Path = DEFAULT_SILVER_PATH
    gold_metrics_path: Path = DEFAULT_GOLD_METRICS_PATH
    spark_master: str = DEFAULT_SPARK_MASTER
    spark_log_level: str = "WARN"

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> GoldConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        return cls(
            silver_path=Path(values.get("SILVER_TABLE_PATH", DEFAULT_SILVER_PATH)),
            gold_metrics_path=Path(
                values.get("GOLD_METRICS_PATH", DEFAULT_GOLD_METRICS_PATH)
            ),
            spark_master=values.get("SPARK_MASTER", DEFAULT_SPARK_MASTER),
            spark_log_level=values.get("SPARK_LOG_LEVEL", "WARN"),
        )
