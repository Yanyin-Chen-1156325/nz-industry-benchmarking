"""Reusable PySpark checks for the implemented Silver AES contract."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import reduce
from operator import or_
from pathlib import Path

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

from nz_industry_benchmarking.ingestion.config import DEFAULT_SCHEMA_VERSION
from nz_industry_benchmarking.quality.contract import (
    BLOCKING,
    INFORMATIONAL,
    QUALITY_RULES,
    SILVER_COLUMN_TYPES,
)
from nz_industry_benchmarking.quality.models import (
    QualityCheckResult,
    QualityReport,
)
from nz_industry_benchmarking.silver.contract import (
    EXPECTED_AGGREGATION_LEVELS,
    EXPECTED_VARIABLE_DEFINITIONS,
    SILVER_SCHEMA_VERSION,
)
from nz_industry_benchmarking.silver.transform import NUMERIC_PATTERN


def assess_silver_quality(
    dataframe: DataFrame,
    *,
    dataset_path: Path | str = "<dataframe>",
    generated_at: datetime | None = None,
) -> QualityReport:
    """Evaluate Silver without filtering or changing any source record."""
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Quality report timestamp must be timezone-aware.")

    rows_processed = dataframe.count()
    schema_checks = _schema_checks(dataframe)
    if any(check.status == "FAIL" for check in schema_checks):
        return _build_report(
            dataset_path=dataset_path,
            timestamp=timestamp,
            rows_processed=rows_processed,
            rows_accepted=0,
            validation_failure_counts={},
            checks=schema_checks,
        )

    observation_window = Window.partitionBy(
        "ingestion_id",
        "year",
        "industry_aggregation_nzsioc",
        "industry_code_nzsioc",
        "variable_code",
    )
    record_window = Window.partitionBy("record_id")
    ingestion_window = Window.partitionBy("ingestion_id")
    source_row_window = Window.partitionBy("ingestion_id", "source_row_number")

    staged = (
        dataframe.withColumn(
            "_dq_observation_count", F.count(F.lit(1)).over(observation_window)
        )
        .withColumn("_dq_record_count", F.count(F.lit(1)).over(record_window))
        .withColumn(
            "_dq_ingestion_count", F.count(F.lit(1)).over(ingestion_window)
        )
        .withColumn(
            "_dq_source_row_count", F.count(F.lit(1)).over(source_row_window)
        )
    )

    value_is_blank = _is_blank("value_raw")
    raw_is_numeric = F.col("value_raw").rlike(NUMERIC_PATTERN)
    published_valid = (
        (F.col("value_status") == "PUBLISHED")
        & raw_is_numeric
        & F.col("value_numeric").isNotNull()
    )
    confidential_valid = (
        (F.col("value_status") == "CONFIDENTIAL")
        & (F.col("value_raw") == "C")
        & F.col("value_numeric").isNull()
    )
    suppressed_valid = (
        (F.col("value_status") == "SUPPRESSED")
        & (F.col("value_raw") == "S")
        & F.col("value_numeric").isNull()
    )
    unavailable_valid = (
        (F.col("value_status") == "UNAVAILABLE")
        & value_is_blank
        & F.col("value_numeric").isNull()
    )
    invalid_valid = (
        (F.col("value_status") == "INVALID")
        & ~value_is_blank
        & ~F.col("value_raw").isin("C", "S")
        & (~raw_is_numeric | F.col("value_numeric").isNull())
        & F.col("value_numeric").isNull()
    )

    required_dimensions = (
        F.col("year").isNull()
        | _is_blank("year_raw")
        | _is_blank("industry_aggregation_nzsioc")
        | _is_blank("industry_code_nzsioc")
        | _is_blank("industry_name_nzsioc")
        | _is_blank("industry_code_anzsic06")
        | _is_blank("variable_code")
        | _is_blank("variable_name")
        | _is_blank("variable_category")
        | _is_blank("units")
    )
    year_invalid = (
        F.col("year").isNull()
        | ~F.col("year_raw").rlike(r"^\d{4}$")
        | (F.col("year") != F.col("year_raw").cast("integer"))
    )
    validation_outcome_invalid = (
        F.col("is_valid").isNull()
        | F.col("record_status").isNull()
        | F.col("validation_rule_ids").isNull()
        | F.col("validation_failure_reasons").isNull()
        | (F.size("validation_rule_ids") != F.size("validation_failure_reasons"))
        | (
            F.col("is_valid")
            != (F.size(F.col("validation_rule_ids")) == F.lit(0))
        )
        | (
            F.col("record_status")
            != F.when(F.col("is_valid"), F.lit("VALID")).otherwise(
                F.lit("INVALID")
            )
        )
    )
    lineage_invalid = (
        _is_blank("record_id")
        | _is_blank("ingestion_id")
        | _is_blank("source_file")
        | _is_blank("source_url")
        | _is_blank("source_sha256")
        | _is_blank("dataset_version")
        | _is_blank("source_schema_version")
        | _is_blank("silver_schema_version")
        | _is_blank("silver_input_fingerprint")
        | F.col("dataset_year").isNull()
        | F.col("ingestion_timestamp").isNull()
        | F.col("source_row_count").isNull()
        | F.col("source_row_number").isNull()
        | F.col("silver_processing_timestamp").isNull()
        | (F.col("ingestion_id") != F.col("source_sha256"))
        | (F.col("source_schema_version") != DEFAULT_SCHEMA_VERSION)
        | (F.col("silver_schema_version") != SILVER_SCHEMA_VERSION)
        | (F.col("source_row_number") < F.lit(1))
        | (F.col("source_row_number") > F.col("source_row_count"))
        | (F.col("_dq_source_row_count") > F.lit(1))
        | (F.col("_dq_ingestion_count") != F.col("source_row_count"))
    )

    blocking_conditions = {
        "DQ_COMPLETENESS_REQUIRED_DIMENSIONS": required_dimensions,
        "DQ_VALIDITY_YEAR": year_invalid,
        "DQ_VALIDITY_AGGREGATION_LEVEL": ~F.col(
            "industry_aggregation_nzsioc"
        ).isin(*EXPECTED_AGGREGATION_LEVELS),
        "DQ_VALIDITY_VARIABLE_DEFINITION": ~_variable_definition_condition(),
        "DQ_VALIDITY_VALUE_STATE": ~F.coalesce(
            (
                published_valid
                | confidential_valid
                | suppressed_valid
                | unavailable_valid
                | invalid_valid
            ),
            F.lit(False),
        ),
        "DQ_UNIQUENESS_RECORD_ID": F.col("_dq_record_count") > F.lit(1),
        "DQ_UNIQUENESS_OBSERVATION_GRAIN": F.col("_dq_observation_count")
        > F.lit(1),
        "DQ_CONTRACT_VALIDATION_OUTCOME": validation_outcome_invalid,
        "DQ_CONTRACT_INVALID_ROWS": ~F.coalesce(F.col("is_valid"), F.lit(False)),
        "DQ_CONTRACT_LINEAGE": lineage_invalid,
    }
    informational_conditions = {
        "DQ_INFO_CONFIDENTIAL_ROWS": F.col("value_status") == "CONFIDENTIAL",
        "DQ_INFO_SUPPRESSED_ROWS": F.col("value_status") == "SUPPRESSED",
        "DQ_INFO_NEGATIVE_PUBLISHED_ROWS": (
            (F.col("value_status") == "PUBLISHED")
            & (F.col("value_numeric") < F.lit(0))
        ),
    }
    all_conditions = {**blocking_conditions, **informational_conditions}
    aggregates = [
        F.sum(F.when(condition, F.lit(1)).otherwise(F.lit(0))).alias(rule_id)
        for rule_id, condition in all_conditions.items()
    ]
    aggregates.append(
        F.sum(
            F.when(F.coalesce(F.col("is_valid"), F.lit(False)), F.lit(1)).otherwise(
                F.lit(0)
            )
        ).alias("_dq_rows_accepted")
    )
    counts = staged.agg(*aggregates).first().asDict()
    validation_failure_counts = {
        row.rule_id: row["count"]
        for row in (
            dataframe.select(F.explode("validation_rule_ids").alias("rule_id"))
            .groupBy("rule_id")
            .count()
            .collect()
        )
    }

    row_checks = tuple(
        _row_check(rule_id, int(counts[rule_id])) for rule_id in all_conditions
    )
    return _build_report(
        dataset_path=dataset_path,
        timestamp=timestamp,
        rows_processed=rows_processed,
        rows_accepted=int(counts["_dq_rows_accepted"]),
        validation_failure_counts=dict(sorted(validation_failure_counts.items())),
        checks=(*schema_checks, *row_checks),
    )


def _schema_checks(dataframe: DataFrame) -> tuple[QualityCheckResult, ...]:
    actual_types = {
        field.name: field.dataType.simpleString() for field in dataframe.schema.fields
    }
    expected = set(SILVER_COLUMN_TYPES)
    actual = set(actual_types)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    mismatches = {
        column: {
            "expected": SILVER_COLUMN_TYPES[column],
            "actual": actual_types[column],
        }
        for column in sorted(expected & actual)
        if actual_types[column] != SILVER_COLUMN_TYPES[column]
    }
    return (
        _schema_check(
            "DQ_SCHEMA_REQUIRED_COLUMNS",
            passed=not missing,
            details="All required columns are present."
            if not missing
            else f"Missing columns: {missing!r}",
        ),
        _schema_check(
            "DQ_SCHEMA_UNEXPECTED_COLUMNS",
            passed=not unexpected,
            details="No unexpected columns are present."
            if not unexpected
            else f"Unexpected columns: {unexpected!r}",
        ),
        _schema_check(
            "DQ_SCHEMA_COLUMN_TYPES",
            passed=not mismatches,
            details="All column types match."
            if not mismatches
            else f"Type mismatches: {mismatches!r}",
        ),
    )


def _schema_check(rule_id: str, *, passed: bool, details: str) -> QualityCheckResult:
    dimension, severity, description = QUALITY_RULES[rule_id]
    return QualityCheckResult(
        rule_id=rule_id,
        dimension=dimension,
        severity=severity,
        status="PASS" if passed else "FAIL",
        description=description,
        affected_rows=None,
        details=details,
    )


def _row_check(rule_id: str, affected_rows: int) -> QualityCheckResult:
    dimension, severity, description = QUALITY_RULES[rule_id]
    informational = severity == INFORMATIONAL
    passed = informational or affected_rows == 0
    if informational:
        details = f"Observed {affected_rows} matching rows; this is not a failure."
    elif passed:
        details = "No affected rows."
    else:
        details = f"Found {affected_rows} affected rows."
    return QualityCheckResult(
        rule_id=rule_id,
        dimension=dimension,
        severity=severity,
        status="PASS" if passed else "FAIL",
        description=description,
        affected_rows=affected_rows,
        details=details,
    )


def _build_report(
    *,
    dataset_path: Path | str,
    timestamp: datetime,
    rows_processed: int,
    rows_accepted: int,
    validation_failure_counts: dict[str, int],
    checks: tuple[QualityCheckResult, ...],
) -> QualityReport:
    failed = sum(check.status == "FAIL" for check in checks)
    blocking_failed = any(
        check.status == "FAIL" and check.severity == BLOCKING for check in checks
    )
    return QualityReport(
        dataset_path=str(dataset_path),
        generated_at=timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        overall_result="FAIL" if blocking_failed else "PASS",
        rows_processed=rows_processed,
        rows_accepted=rows_accepted,
        rows_rejected=rows_processed - rows_accepted,
        checks_executed=len(checks),
        passed_checks=len(checks) - failed,
        failed_checks=failed,
        validation_failure_counts=validation_failure_counts,
        checks=checks,
    )


def _is_blank(column: str) -> Column:
    value = F.col(column)
    return value.isNull() | (F.length(F.trim(value)) == 0)


def _variable_definition_condition() -> Column:
    conditions = (
        (F.col("variable_code") == code)
        & (F.col("variable_name") == name)
        & (F.col("variable_category") == category)
        & (F.col("units") == units)
        for code, name, category, units in EXPECTED_VARIABLE_DEFINITIONS
    )
    return reduce(or_, conditions, F.lit(False))
