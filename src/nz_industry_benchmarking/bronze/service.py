"""Orchestration between the approved ingestion output and Bronze Delta."""

from __future__ import annotations

from pyspark.sql import SparkSession

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.bronze.schema import build_bronze_dataframe
from nz_industry_benchmarking.bronze.writer import write_bronze
from nz_industry_benchmarking.ingestion.models import IngestionOutcome


def persist_ingestion(
    spark: SparkSession,
    outcome: IngestionOutcome,
    config: BronzeConfig,
) -> BronzeWriteResult:
    """Persist an approved Phase 3 ingestion outcome to Bronze."""
    dataframe = build_bronze_dataframe(spark, outcome)
    return write_bronze(
        spark,
        dataframe,
        config.table_path,
        ingestion_id=outcome.metadata.ingestion_id,
        source_sha256=outcome.metadata.source_sha256,
        expected_rows=outcome.metadata.row_count,
    )
