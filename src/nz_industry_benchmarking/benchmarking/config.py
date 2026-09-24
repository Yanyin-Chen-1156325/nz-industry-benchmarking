"""Runtime configuration for Gold benchmark queries."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.bronze.config import DEFAULT_SPARK_MASTER
from nz_industry_benchmarking.gold.config import DEFAULT_GOLD_METRICS_PATH


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Gold source and Spark settings for a ranking query."""

    gold_metrics_path: Path = DEFAULT_GOLD_METRICS_PATH
    spark_master: str = DEFAULT_SPARK_MASTER
    spark_log_level: str = "WARN"

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> BenchmarkConfig:
        """Build settings from environment variables and project defaults."""
        values = os.environ if environ is None else environ
        return cls(
            gold_metrics_path=Path(
                values.get("GOLD_METRICS_PATH", DEFAULT_GOLD_METRICS_PATH)
            ),
            spark_master=values.get("SPARK_MASTER", DEFAULT_SPARK_MASTER),
            spark_log_level=values.get("SPARK_LOG_LEVEL", "WARN"),
        )
