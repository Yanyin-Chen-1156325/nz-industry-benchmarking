"""Thin Databricks orchestration over shared ingestion and transformations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pyspark.sql import SparkSession

from nz_industry_benchmarking.bronze.schema import build_bronze_dataframe
from nz_industry_benchmarking.bronze.writer import write_bronze_to_storage
from nz_industry_benchmarking.databricks.config import DatabricksInitialLoadConfig
from nz_industry_benchmarking.databricks.errors import DatabricksInitialLoadError
from nz_industry_benchmarking.databricks.models import DatabricksInitialLoadResult
from nz_industry_benchmarking.gold.service import calculate_gold_input_fingerprint
from nz_industry_benchmarking.gold.transform import transform_silver_to_gold
from nz_industry_benchmarking.gold.writer import write_gold_to_storage
from nz_industry_benchmarking.ingestion.service import prepare_ingestion
from nz_industry_benchmarking.quality.evaluator import assess_silver_quality
from nz_industry_benchmarking.silver.current_view import select_current_bronze_view
from nz_industry_benchmarking.silver.service import calculate_input_fingerprint
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver
from nz_industry_benchmarking.silver.writer import write_silver_to_storage
from nz_industry_benchmarking.storage import CatalogDeltaStorage


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def run_initial_load(
    spark: SparkSession,
    config: DatabricksInitialLoadConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> DatabricksInitialLoadResult:
    """Run the initial managed-table Bronze -> Silver -> Gold pipeline.

    The caller owns ``spark``. This function does not configure, create, stop,
    or access ``spark.sparkContext`` and is therefore safe for a Databricks
    Serverless-provided SparkSession.
    """
    bronze_storage = CatalogDeltaStorage(spark, config.bronze_target)
    silver_storage = CatalogDeltaStorage(spark, config.silver_target)
    gold_storage = CatalogDeltaStorage(spark, config.gold_target)

    outcome = prepare_ingestion(config.ingestion, clock=clock)
    _require_initial_or_same_bronze(bronze_storage, outcome.metadata.ingestion_id)
    bronze_frame = build_bronze_dataframe(spark, outcome)
    bronze_result = write_bronze_to_storage(
        bronze_frame,
        bronze_storage,
        ingestion_id=outcome.metadata.ingestion_id,
        source_sha256=outcome.metadata.source_sha256,
        expected_rows=outcome.metadata.row_count,
    )

    bronze = bronze_storage.read()
    silver_fingerprint = calculate_input_fingerprint(bronze)
    current_bronze = select_current_bronze_view(bronze)
    bronze_input_rows = current_bronze.count()
    silver_frame = transform_bronze_to_silver(
        current_bronze,
        input_fingerprint=silver_fingerprint,
        processing_timestamp=clock(),
    )
    silver_result = write_silver_to_storage(
        silver_frame,
        silver_storage,
        input_fingerprint=silver_fingerprint,
        bronze_input_rows=bronze_input_rows,
    )

    stored_silver = silver_storage.read()
    quality = assess_silver_quality(
        stored_silver,
        dataset_path=silver_storage.identifier,
        generated_at=clock(),
    )

    gold_fingerprint = calculate_gold_input_fingerprint(stored_silver)
    gold_frame = transform_silver_to_gold(
        stored_silver,
        input_fingerprint=gold_fingerprint,
        processing_timestamp=clock(),
    )
    expected_gold_rows = gold_frame.count()
    gold_result = write_gold_to_storage(
        gold_frame,
        gold_storage,
        input_fingerprint=gold_fingerprint,
        silver_input_rows=silver_result.silver_output_rows,
        expected_gold_rows=expected_gold_rows,
    )
    return DatabricksInitialLoadResult(
        bronze=bronze_result,
        silver=silver_result,
        quality=quality,
        gold=gold_result,
    )


def _require_initial_or_same_bronze(
    storage: CatalogDeltaStorage,
    ingestion_id: str,
) -> None:
    """Reject unrelated Bronze history until incremental migration is approved."""
    if not storage.exists():
        return
    identities = {
        row.ingestion_id
        for row in storage.read().select("ingestion_id").distinct().collect()
    }
    if identities and identities != {ingestion_id}:
        raise DatabricksInitialLoadError(
            "The Bronze managed table contains a different ingestion. Phase 15 "
            "Step 1 supports only an empty target or an idempotent rerun of the "
            "same source artifact."
        )
