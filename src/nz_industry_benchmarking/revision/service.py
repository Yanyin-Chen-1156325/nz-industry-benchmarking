"""Revision-aware orchestration entered from Phase 9 deferred artifacts."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from delta.tables import DeltaTable
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.schema import build_bronze_dataframe
from nz_industry_benchmarking.bronze.service import persist_ingestion
from nz_industry_benchmarking.gold.service import process_gold
from nz_industry_benchmarking.incremental.inspector import inspect_pipeline_state
from nz_industry_benchmarking.incremental.planner import plan_incremental_processing
from nz_industry_benchmarking.ingestion.service import ingest
from nz_industry_benchmarking.revision.analyzer import PRECEDENCE_RULE, analyze_revision
from nz_industry_benchmarking.revision.audit import (
    read_report,
    report_path,
    write_report,
)
from nz_industry_benchmarking.revision.config import RevisionConfig
from nz_industry_benchmarking.revision.errors import RevisionSourceError
from nz_industry_benchmarking.revision.models import RevisionReport, RevisionRunResult
from nz_industry_benchmarking.silver.service import process_silver


def run_revision_pipeline(
    spark: SparkSession,
    config: RevisionConfig,
) -> RevisionRunResult:
    """Classify and safely apply one newer official overlapping release."""
    outcome = ingest(config.pipeline.ingestion)
    audit_path = report_path(config.report_dir, outcome.metadata.source_sha256)
    existing_report = read_report(audit_path)
    if existing_report is not None:
        return RevisionRunResult(existing_report, duplicate=True)

    state = inspect_pipeline_state(spark, outcome, config.pipeline)
    phase9_plan = plan_incremental_processing(outcome.metadata, state)
    bronze_uri = config.pipeline.bronze.table_path.resolve().as_uri()
    if not DeltaTable.isDeltaTable(spark, bronze_uri):
        report = _non_revision_report(outcome.metadata.to_dict(), "NOT_REVISION")
        return RevisionRunResult(report, duplicate=False)

    bronze = spark.read.format("delta").load(bronze_uri)
    history = bronze.where(F.col("ingestion_id") != outcome.metadata.ingestion_id)
    if history.limit(1).count() == 0:
        report = _non_revision_report(outcome.metadata.to_dict(), "NO_OP")
        return RevisionRunResult(report, duplicate=False)
    candidate = build_bronze_dataframe(spark, outcome)
    report = analyze_revision(candidate, history, outcome.metadata)

    if report.overall_result != "ELIGIBLE":
        write_report(audit_path, report)
        return RevisionRunResult(report, duplicate=False)
    if phase9_plan.pipeline_status not in {"DEFERRED_REVISION", "PROCESS_REQUIRED"}:
        raise RevisionSourceError(
            f"Unexpected Phase 9 entry state: {phase9_plan.pipeline_status}."
        )

    bronze_result = persist_ingestion(spark, outcome, config.pipeline.bronze)
    silver_result = process_silver(spark, config.pipeline.silver)
    gold_result = process_gold(spark, config.pipeline.gold)
    applied = replace(
        report,
        overall_result="APPLIED",
        message=(
            "Newer official release was preserved in Bronze and selected in the "
            "deterministic Silver current view; Gold was refreshed."
        ),
    )
    write_report(audit_path, applied)
    return RevisionRunResult(
        report=applied,
        duplicate=False,
        bronze_result=bronze_result,
        silver_result=silver_result,
        gold_result=gold_result,
    )


def _non_revision_report(
    incoming: dict[str, object],
    result: str,
) -> RevisionReport:
    source_sha256 = str(incoming["source_sha256"])
    revision_id = hashlib.sha256(
        f"aes-revision-v1\n{source_sha256}".encode()
    ).hexdigest().upper()
    return RevisionReport(
        revision_id=revision_id,
        overall_result=result,
        precedence_rule=PRECEDENCE_RULE,
        previous_releases=(),
        incoming_release=incoming,
        overlapping_observations=0,
        unchanged_republications=0,
        revised_values=0,
        revised_metadata=0,
        newly_added_observations=0,
        observations_absent_from_incoming=0,
        current_view_observations_changed=0,
        value_transition_counts={},
        silver_rebuild_required=False,
        gold_rebuild_required=False,
        message="The artifact is already current or is not an overlapping revision.",
    )
