"""Service boundary for assessing Silver Delta and persisting its report."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from delta.tables import DeltaTable
from pyspark.sql import SparkSession

from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.quality.config import QualityConfig
from nz_industry_benchmarking.quality.errors import QualitySourceError
from nz_industry_benchmarking.quality.evaluator import assess_silver_quality
from nz_industry_benchmarking.quality.models import QualityReport

logger = logging.getLogger(LOGGER_NAME)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def run_quality_assessment(
    spark: SparkSession,
    config: QualityConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> QualityReport:
    """Read Silver Delta, assess it, and atomically persist a JSON report."""
    silver_path = config.silver_path.resolve()
    silver_uri = silver_path.as_uri()
    if not DeltaTable.isDeltaTable(spark, silver_uri):
        raise QualitySourceError(
            f"Silver Delta table does not exist or is invalid: {silver_path}"
        )

    logger.info(
        "quality_assessment_started",
        extra={"silver_path": silver_path.as_posix()},
    )
    silver = spark.read.format("delta").load(silver_uri)
    report = assess_silver_quality(
        silver,
        dataset_path=silver_path.as_posix(),
        generated_at=clock(),
    )
    _write_report(report, config.report_path)
    logger.info(
        "quality_assessment_completed",
        extra={
            "silver_path": silver_path.as_posix(),
            "quality_report_path": config.report_path.resolve().as_posix(),
            "quality_result": report.overall_result,
            "row_count": report.rows_processed,
            "valid_rows": report.rows_accepted,
            "invalid_rows": report.rows_rejected,
            "failed_checks": report.failed_checks,
        },
    )
    return report


def _write_report(report: QualityReport, report_path: Path) -> None:
    resolved = report_path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(f".{resolved.name}.tmp")
    temporary.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, resolved)
