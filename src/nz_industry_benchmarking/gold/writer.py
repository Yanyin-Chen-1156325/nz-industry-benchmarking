"""Idempotent snapshot writer for the Gold metric Delta table."""

from __future__ import annotations

import logging
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from nz_industry_benchmarking.gold.contract import GOLD_SCHEMA_VERSION
from nz_industry_benchmarking.gold.errors import GoldIntegrityError
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.storage import (
    DeltaStorage,
    LocalDeltaStorage,
    LocalPathTarget,
)

logger = logging.getLogger(LOGGER_NAME)


def write_gold(
    spark: SparkSession,
    dataframe: DataFrame,
    table_path: Path,
    *,
    input_fingerprint: str,
    silver_input_rows: int,
    expected_gold_rows: int,
) -> GoldWriteResult:
    """Write one complete Gold snapshot without logical duplication."""
    storage = LocalDeltaStorage(spark, LocalPathTarget(table_path))
    return write_gold_to_storage(
        dataframe,
        storage,
        input_fingerprint=input_fingerprint,
        silver_input_rows=silver_input_rows,
        expected_gold_rows=expected_gold_rows,
    )


def write_gold_to_storage(
    dataframe: DataFrame,
    storage: DeltaStorage,
    *,
    input_fingerprint: str,
    silver_input_rows: int,
    expected_gold_rows: int,
) -> GoldWriteResult:
    """Write one Gold snapshot through either supported storage adapter."""
    target = storage.identifier

    if storage.exists():
        existing = storage.read()
        fingerprints = {
            row.gold_input_fingerprint
            for row in existing.select("gold_input_fingerprint").distinct().collect()
        }
        schema_versions = {
            row.gold_schema_version
            for row in existing.select("gold_schema_version").distinct().collect()
        }
        if fingerprints == {input_fingerprint}:
            if schema_versions != {GOLD_SCHEMA_VERSION}:
                raise GoldIntegrityError(
                    "Stored Gold snapshot has an unexpected schema version."
                )
            if existing.count() != expected_gold_rows:
                raise GoldIntegrityError(
                    "Stored Gold snapshot has the expected fingerprint but an "
                    "unexpected row count."
                )
            logger.info(
                "gold_duplicate_input_skipped",
                extra={
                    "gold_path": target,
                    "row_count": expected_gold_rows,
                    "duplicate": True,
                },
            )
            return _summarise(
                existing,
                target,
                input_fingerprint,
                silver_input_rows,
                duplicate=True,
            )

    logger.info(
        "gold_write_started",
        extra={
            "gold_path": target,
            "row_count": expected_gold_rows,
            "duplicate": False,
        },
    )
    storage.write(
        dataframe,
        mode="overwrite",
        options={
            "overwriteSchema": "true",
            "txnAppId": f"nz-industry-benchmarking-gold:{input_fingerprint}",
            "txnVersion": 0,
        },
    )
    stored = storage.read()
    if stored.count() != expected_gold_rows:
        raise GoldIntegrityError(
            "Gold output row count does not match the transformed row count."
        )
    result = _summarise(
        stored,
        target,
        input_fingerprint,
        silver_input_rows,
        duplicate=False,
    )
    logger.info(
        "gold_write_completed",
        extra={
            "gold_path": target,
            "row_count": result.gold_output_rows,
            "duplicate": False,
        },
    )
    return result


def _summarise(
    dataframe: DataFrame,
    table_path: str,
    input_fingerprint: str,
    silver_input_rows: int,
    *,
    duplicate: bool,
) -> GoldWriteResult:
    metric_counts = {
        row.metric_id: row["count"]
        for row in dataframe.groupBy("metric_id").count().collect()
    }
    status_counts = {
        row.metric_status: row["count"]
        for row in dataframe.groupBy("metric_status").count().collect()
    }
    return GoldWriteResult(
        table_path=table_path,
        input_fingerprint=input_fingerprint,
        silver_input_rows=silver_input_rows,
        gold_output_rows=dataframe.count(),
        metric_counts=dict(sorted(metric_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
        duplicate=duplicate,
    )
