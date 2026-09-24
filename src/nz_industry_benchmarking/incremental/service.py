"""Small dependency-aware executor for the existing pipeline components."""

from __future__ import annotations

import logging

from pyspark.sql import SparkSession

from nz_industry_benchmarking.bronze.service import persist_ingestion
from nz_industry_benchmarking.gold.service import process_gold
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.inspector import inspect_pipeline_state
from nz_industry_benchmarking.incremental.models import IncrementalRunResult
from nz_industry_benchmarking.incremental.planner import plan_incremental_processing
from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.ingestion.service import ingest
from nz_industry_benchmarking.silver.service import process_silver

logger = logging.getLogger(LOGGER_NAME)


def run_incremental_pipeline(
    spark: SparkSession,
    config: IncrementalConfig,
) -> IncrementalRunResult:
    """Ingest, plan, and execute only required safe downstream work."""
    outcome = ingest(config.ingestion)
    initial_state = inspect_pipeline_state(spark, outcome, config)
    initial_plan = plan_incremental_processing(outcome.metadata, initial_state)
    logger.info(
        "incremental_plan_created",
        extra={
            "source_file": outcome.metadata.source_file,
            "source_sha256": outcome.metadata.source_sha256,
            "dataset_year": outcome.metadata.dataset_year,
            "dataset_version": outcome.metadata.dataset_version,
            "pipeline_status": initial_plan.pipeline_status,
            "artifact_status": initial_plan.artifact_status,
            "bronze_action": initial_plan.bronze.action,
            "silver_action": initial_plan.silver.action,
            "gold_action": initial_plan.gold.action,
            "revision_sensitive": initial_plan.revision_sensitive,
        },
    )

    if initial_plan.pipeline_status == "DEFERRED_REVISION":
        logger.warning(
            "incremental_revision_deferred",
            extra={
                "source_sha256": outcome.metadata.source_sha256,
                "overlap_observations": initial_plan.overlap_observations,
                "changed_observations": (
                    initial_plan.changed_existing_observations
                ),
            },
        )
        return IncrementalRunResult(initial_plan, initial_plan)

    if initial_plan.pipeline_status == "NO_OP":
        logger.info(
            "incremental_no_op",
            extra={
                "source_sha256": outcome.metadata.source_sha256,
                "pipeline_status": initial_plan.pipeline_status,
                "bronze_action": initial_plan.bronze.action,
                "silver_action": initial_plan.silver.action,
                "gold_action": initial_plan.gold.action,
            },
        )
        return IncrementalRunResult(initial_plan, initial_plan)

    bronze_result = None
    silver_result = None
    gold_result = None
    if initial_plan.bronze.action == "REQUIRED":
        bronze_result = persist_ingestion(spark, outcome, config.bronze)
    if initial_plan.silver.action == "REQUIRED":
        silver_result = process_silver(spark, config.silver)
    if initial_plan.gold.action == "REQUIRED":
        gold_result = process_gold(spark, config.gold)

    final_state = inspect_pipeline_state(spark, outcome, config)
    final_plan = plan_incremental_processing(outcome.metadata, final_state)
    logger.info(
        "incremental_pipeline_completed",
        extra={
            "source_sha256": outcome.metadata.source_sha256,
            "pipeline_status": final_plan.pipeline_status,
            "bronze_action": final_plan.bronze.action,
            "silver_action": final_plan.silver.action,
            "gold_action": final_plan.gold.action,
        },
    )
    return IncrementalRunResult(
        initial_plan=initial_plan,
        final_plan=final_plan,
        bronze_result=bronze_result,
        silver_result=silver_result,
        gold_result=gold_result,
    )
