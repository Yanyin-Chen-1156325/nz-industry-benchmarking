"""Orchestration from Silver Delta to the Gold metrics Delta table."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession

from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.gold.contract import (
    GOLD_LOGIC_VERSION,
    GOLD_SCHEMA_VERSION,
)
from nz_industry_benchmarking.gold.errors import GoldSourceError
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.gold.transform import (
    transform_silver_to_gold,
    validate_silver_schema,
)
from nz_industry_benchmarking.gold.writer import write_gold


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def process_gold(
    spark: SparkSession,
    config: GoldConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> GoldWriteResult:
    """Read only Silver Delta, calculate M1-M7, and persist Gold Delta."""
    silver_path = config.silver_path.resolve()
    silver_uri = silver_path.as_uri()
    if not DeltaTable.isDeltaTable(spark, silver_uri):
        raise GoldSourceError(
            f"Silver Delta table does not exist or is invalid: {silver_path}"
        )

    silver = spark.read.format("delta").load(silver_uri)
    silver_input_rows = silver.count()
    if silver_input_rows == 0:
        raise GoldSourceError(f"Silver Delta table contains no rows: {silver_path}")
    validate_silver_schema(silver)

    input_fingerprint = calculate_gold_input_fingerprint(silver)
    gold = transform_silver_to_gold(
        silver,
        input_fingerprint=input_fingerprint,
        processing_timestamp=clock(),
    )
    gold_output_rows = gold.count()
    return write_gold(
        spark,
        gold,
        config.gold_metrics_path,
        input_fingerprint=input_fingerprint,
        silver_input_rows=silver_input_rows,
        expected_gold_rows=gold_output_rows,
    )


def calculate_gold_input_fingerprint(silver: DataFrame) -> str:
    """Hash Silver snapshot identities together with the Gold contract version."""
    fingerprints = {
        row.silver_input_fingerprint
        for row in silver.select("silver_input_fingerprint").distinct().collect()
    }
    return calculate_gold_input_fingerprint_from_silver(fingerprints)


def calculate_gold_input_fingerprint_from_silver(
    fingerprints: set[str] | frozenset[str],
) -> str:
    """Hash Silver fingerprints with the implemented Gold contract versions."""
    payload = "\n".join(
        [GOLD_SCHEMA_VERSION, GOLD_LOGIC_VERSION, *sorted(fingerprints)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
