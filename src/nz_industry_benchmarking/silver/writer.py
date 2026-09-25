"""Idempotent snapshot writer for the Silver Delta table."""

from __future__ import annotations

import logging
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.silver.errors import SilverIntegrityError
from nz_industry_benchmarking.silver.models import SilverWriteResult
from nz_industry_benchmarking.storage import (
    DeltaStorage,
    LocalDeltaStorage,
    LocalPathTarget,
)

logger = logging.getLogger(LOGGER_NAME)


def write_silver(
    spark: SparkSession,
    dataframe: DataFrame,
    table_path: Path,
    *,
    input_fingerprint: str,
    bronze_input_rows: int,
) -> SilverWriteResult:
    """Write one deterministic Silver snapshot without logical duplication."""
    storage = LocalDeltaStorage(spark, LocalPathTarget(table_path))
    return write_silver_to_storage(
        dataframe,
        storage,
        input_fingerprint=input_fingerprint,
        bronze_input_rows=bronze_input_rows,
    )


def write_silver_to_storage(
    dataframe: DataFrame,
    storage: DeltaStorage,
    *,
    input_fingerprint: str,
    bronze_input_rows: int,
) -> SilverWriteResult:
    """Write one Silver snapshot through either supported storage adapter."""
    target = storage.identifier

    if storage.exists():
        existing = storage.read()
        fingerprints = {
            row.silver_input_fingerprint
            for row in existing.select("silver_input_fingerprint")
            .distinct()
            .collect()
        }
        if fingerprints == {input_fingerprint}:
            if existing.count() != bronze_input_rows:
                raise SilverIntegrityError(
                    "Stored Silver snapshot has the expected fingerprint but an "
                    "unexpected row count."
                )
            logger.info(
                "silver_duplicate_input_skipped",
                extra={
                    "silver_path": target,
                    "row_count": bronze_input_rows,
                    "duplicate": True,
                },
            )
            return _summarise(
                existing,
                target,
                input_fingerprint,
                bronze_input_rows,
                duplicate=True,
            )

    logger.info(
        "silver_write_started",
        extra={
            "silver_path": target,
            "row_count": bronze_input_rows,
            "duplicate": False,
        },
    )
    storage.write(
        dataframe,
        mode="overwrite",
        options={
            "overwriteSchema": "true",
            "txnAppId": f"nz-industry-benchmarking-silver:{input_fingerprint}",
            "txnVersion": 0,
        },
    )
    stored = storage.read()
    if stored.count() != bronze_input_rows:
        raise SilverIntegrityError(
            "Silver output row count does not match the Bronze input row count."
        )
    result = _summarise(
        stored,
        target,
        input_fingerprint,
        bronze_input_rows,
        duplicate=False,
    )
    logger.info(
        "silver_write_completed",
        extra={
            "silver_path": target,
            "row_count": result.silver_output_rows,
            "valid_rows": result.valid_rows,
            "invalid_rows": result.invalid_rows,
            "duplicate": False,
        },
    )
    return result


def _summarise(
    dataframe: DataFrame,
    table_path: str,
    input_fingerprint: str,
    bronze_input_rows: int,
    *,
    duplicate: bool,
) -> SilverWriteResult:
    counts = {
        row.value_status: row["count"]
        for row in dataframe.groupBy("value_status").count().collect()
    }
    valid_rows = dataframe.where(F.col("is_valid")).count()
    output_rows = dataframe.count()
    return SilverWriteResult(
        table_path=table_path,
        input_fingerprint=input_fingerprint,
        bronze_input_rows=bronze_input_rows,
        silver_output_rows=output_rows,
        valid_rows=valid_rows,
        invalid_rows=output_rows - valid_rows,
        status_counts=dict(sorted(counts.items())),
        duplicate=duplicate,
    )
