"""Idempotent Delta writer for one logical AES ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.errors import BronzeIntegrityError
from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME

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
    resolved_path = table_path.resolve()
    delta_path = resolved_path.as_uri()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "bronze_write_started",
        extra={
            "bronze_path": resolved_path.as_posix(),
            "ingestion_id": ingestion_id,
            "source_sha256": source_sha256,
            "row_count": expected_rows,
        },
    )

    if DeltaTable.isDeltaTable(spark, delta_path):
        existing = spark.read.format("delta").load(delta_path)
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
                    "bronze_path": resolved_path.as_posix(),
                    "ingestion_id": ingestion_id,
                    "source_sha256": source_sha256,
                    "row_count": existing_rows,
                    "inserted_rows": 0,
                    "total_rows": total_rows,
                    "duplicate": True,
                },
            )
            return BronzeWriteResult(
                table_path=resolved_path.as_posix(),
                ingestion_id=ingestion_id,
                source_sha256=source_sha256,
                input_rows=expected_rows,
                inserted_rows=0,
                total_rows=total_rows,
                duplicate=True,
            )

    (
        dataframe.write.format("delta")
        .mode("append")
        .option("txnAppId", f"nz-industry-benchmarking:{ingestion_id}")
        .option("txnVersion", 0)
        .save(delta_path)
    )
    stored = spark.read.format("delta").load(delta_path)
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
            "bronze_path": resolved_path.as_posix(),
            "ingestion_id": ingestion_id,
            "source_sha256": source_sha256,
            "row_count": stored_rows,
            "inserted_rows": stored_rows,
            "total_rows": total_rows,
            "duplicate": False,
        },
    )
    return BronzeWriteResult(
        table_path=resolved_path.as_posix(),
        ingestion_id=ingestion_id,
        source_sha256=source_sha256,
        input_rows=expected_rows,
        inserted_rows=stored_rows,
        total_rows=total_rows,
        duplicate=False,
    )
