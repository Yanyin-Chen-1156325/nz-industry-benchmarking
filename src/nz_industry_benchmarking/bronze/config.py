"""Runtime configuration for the Bronze Delta layer."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BRONZE_PATH = Path("data/bronze/aes")
DEFAULT_SPARK_MASTER = "local[2]"


@dataclass(frozen=True, slots=True)
class BronzeConfig:
    """Settings needed to create Spark and persist the Bronze table."""

    table_path: Path = DEFAULT_BRONZE_PATH
    spark_master: str = DEFAULT_SPARK_MASTER
    spark_log_level: str = "WARN"

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> BronzeConfig:
        """Build Bronze settings from environment variables and defaults."""
        values = os.environ if environ is None else environ
        return cls(
            table_path=Path(values.get("BRONZE_TABLE_PATH", DEFAULT_BRONZE_PATH)),
            spark_master=values.get("SPARK_MASTER", DEFAULT_SPARK_MASTER),
            spark_log_level=values.get("SPARK_LOG_LEVEL", "WARN"),
        )
