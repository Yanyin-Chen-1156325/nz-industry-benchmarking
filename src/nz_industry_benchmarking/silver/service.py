"""Orchestration from the Bronze Delta boundary to Silver Delta."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession

from nz_industry_benchmarking.silver.config import SilverConfig
from nz_industry_benchmarking.silver.errors import SilverSourceError
from nz_industry_benchmarking.silver.models import SilverWriteResult
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver
from nz_industry_benchmarking.silver.writer import write_silver


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def process_silver(
    spark: SparkSession,
    config: SilverConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> SilverWriteResult:
    """Read only Bronze Delta, transform every row, and persist Silver."""
    bronze_path = config.bronze_path.resolve()
    bronze_uri = bronze_path.as_uri()
    if not DeltaTable.isDeltaTable(spark, bronze_uri):
        raise SilverSourceError(
            f"Bronze Delta table does not exist or is invalid: {bronze_path}"
        )

    bronze = spark.read.format("delta").load(bronze_uri)
    bronze_input_rows = bronze.count()
    if bronze_input_rows == 0:
        raise SilverSourceError(f"Bronze Delta table contains no rows: {bronze_path}")

    input_fingerprint = calculate_input_fingerprint(bronze)
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint=input_fingerprint,
        processing_timestamp=clock(),
    )
    return write_silver(
        spark,
        silver,
        config.silver_path,
        input_fingerprint=input_fingerprint,
        bronze_input_rows=bronze_input_rows,
    )


def calculate_input_fingerprint(bronze: DataFrame) -> str:
    """Hash the sorted set of Bronze artifact identities deterministically."""
    identities = sorted(
        (row.ingestion_id, row.source_sha256)
        for row in bronze.select("ingestion_id", "source_sha256")
        .distinct()
        .collect()
    )
    payload = "\n".join(
        f"{ingestion_id}:{digest}" for ingestion_id, digest in identities
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
