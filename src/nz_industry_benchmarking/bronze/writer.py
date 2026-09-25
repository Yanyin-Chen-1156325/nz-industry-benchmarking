"""Idempotent Delta writer for one logical AES ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.errors import BronzeIntegrityError
from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.storage import (
    DeltaStorage,
    LocalDeltaStorage,
    LocalPathTarget,
)

logger = logging.getLogger(LOGGER_NAME)


def write_bronze(
    spark: SparkSession,
    dataframe: DataFrame,
    table_path: Path,
    *,
    ingestion_id: str,
    source_sha256: str,
    expected_rows: int,
) -> BronzeWriteResult:
    """Append one source artifact exactly once to a Delta table."""
    storage = LocalDeltaStorage(spark, LocalPathTarget(table_path))
    return write_bronze_to_storage(
        dataframe,
        storage,
        ingestion_id=ingestion_id,
        source_sha256=source_sha256,
        expected_rows=expected_rows,
    )


def write_bronze_to_storage(
    dataframe: DataFrame,
    storage: DeltaStorage,
    *,
    ingestion_id: str,
    source_sha256: str,
    expected_rows: int,
) -> BronzeWriteResult:
    """Append one source artifact through either supported storage adapter."""
    target = storage.identifier
    logger.info(
        "bronze_write_started",
        extra={
            "bronze_path": target,
            "ingestion_id": ingestion_id,
            "source_sha256": source_sha256,
            "row_count": expected_rows,
        },
    )

    if storage.exists():
        existing = storage.read()
        existing_rows = existing.where(F.col("ingestion_id") == ingestion_id).count()
        if existing_rows:
            if existing_rows != expected_rows:
                raise BronzeIntegrityError(
                    "Bronze contains a partial or conflicting logical ingestion: "
                    f"expected {expected_rows} rows for {ingestion_id}, "
                    f"found {existing_rows}."
                )
            total_rows = existing.count()
            logger.info(
                "bronze_duplicate_ingestion_skipped",
                extra={
                    "bronze_path": target,
                    "ingestion_id": ingestion_id,
                    "source_sha256": source_sha256,
                    "row_count": existing_rows,
                    "inserted_rows": 0,
                    "total_rows": total_rows,
                    "duplicate": True,
                },
            )
            return BronzeWriteResult(
                table_path=target,
                ingestion_id=ingestion_id,
                source_sha256=source_sha256,
                input_rows=expected_rows,
                inserted_rows=0,
                total_rows=total_rows,
                duplicate=True,
            )

    storage.write(
        dataframe,
        mode="append",
        options={
            "txnAppId": f"nz-industry-benchmarking:{ingestion_id}",
            "txnVersion": 0,
        },
    )
    stored = storage.read()
    stored_rows = stored.where(F.col("ingestion_id") == ingestion_id).count()
    if stored_rows != expected_rows:
        raise BronzeIntegrityError(
            f"Bronze verification expected {expected_rows} rows for {ingestion_id}, "
            f"found {stored_rows}."
        )
    total_rows = stored.count()
    logger.info(
        "bronze_write_completed",
        extra={
            "bronze_path": target,
            "ingestion_id": ingestion_id,
            "source_sha256": source_sha256,
            "row_count": stored_rows,
            "inserted_rows": stored_rows,
            "total_rows": total_rows,
            "duplicate": False,
        },
    )
    return BronzeWriteResult(
        table_path=target,
        ingestion_id=ingestion_id,
        source_sha256=source_sha256,
        input_rows=expected_rows,
        inserted_rows=stored_rows,
        total_rows=total_rows,
        duplicate=False,
    )
