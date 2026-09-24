"""Phase 6 quality framework behavior against reusable synthetic Silver data."""

from __future__ import annotations

from datetime import UTC, datetime

from pyspark.sql import functions as F

from nz_industry_benchmarking.quality.evaluator import assess_silver_quality
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver

REPORT_TIME = datetime(2026, 9, 24, 3, 4, 5, tzinfo=UTC)


def _silver(bronze):
    return transform_bronze_to_silver(
        bronze,
        input_fingerprint="QUALITY-FRAMEWORK-TEST",
        processing_timestamp=REPORT_TIME,
    )


def _checks(report):
    return {check.rule_id: check for check in report.checks}


def test_valid_protected_and_negative_rows_pass(bronze_dataframe_factory) -> None:
    bronze = bronze_dataframe_factory(
        {"Value": "-810"},
        {"Industry_code_NZSIOC": "BB", "Value": "C"},
        {"Industry_code_NZSIOC": "CC", "Value": "S"},
    )

    report = assess_silver_quality(_silver(bronze), generated_at=REPORT_TIME)
    checks = _checks(report)

    assert report.overall_result == "PASS"
    assert report.rows_processed == 3
    assert report.rows_accepted == 3
    assert report.rows_rejected == 0
    assert checks["DQ_INFO_CONFIDENTIAL_ROWS"].affected_rows == 1
    assert checks["DQ_INFO_SUPPRESSED_ROWS"].affected_rows == 1
    assert checks["DQ_INFO_NEGATIVE_PUBLISHED_ROWS"].affected_rows == 1
    assert all(check.status == "PASS" for check in report.checks)


def test_duplicate_observations_fail_and_remain_counted(
    bronze_dataframe_factory,
) -> None:
    silver = _silver(bronze_dataframe_factory({}, {}))

    report = assess_silver_quality(silver, generated_at=REPORT_TIME)
    checks = _checks(report)

    assert report.overall_result == "FAIL"
    assert report.rows_processed == 2
    assert report.rows_accepted == 0
    assert report.rows_rejected == 2
    assert checks["DQ_UNIQUENESS_OBSERVATION_GRAIN"].status == "FAIL"
    assert checks["DQ_UNIQUENESS_OBSERVATION_GRAIN"].affected_rows == 2
    assert checks["DQ_CONTRACT_INVALID_ROWS"].affected_rows == 2


def test_invalid_metadata_and_value_fail_separate_rules(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {
            "Variable_name": "Invented label",
            "Value": "not-a-number",
        }
    )

    report = assess_silver_quality(_silver(bronze), generated_at=REPORT_TIME)
    checks = _checks(report)

    assert report.overall_result == "FAIL"
    assert report.rows_processed == 1
    assert report.rows_rejected == 1
    assert checks["DQ_VALIDITY_VARIABLE_DEFINITION"].affected_rows == 1
    assert checks["DQ_VALIDITY_VALUE_STATE"].affected_rows == 0
    assert checks["DQ_CONTRACT_INVALID_ROWS"].affected_rows == 1
    assert report.validation_failure_counts == {
        "VALUE_INVALID": 1,
        "VARIABLE_DEFINITION_UNEXPECTED": 1,
    }


def test_schema_change_returns_inspectable_failure(
    bronze_dataframe_factory,
) -> None:
    silver = _silver(bronze_dataframe_factory({})).drop("units")

    report = assess_silver_quality(silver, generated_at=REPORT_TIME)
    checks = _checks(report)

    assert report.overall_result == "FAIL"
    assert report.checks_executed == 3
    assert checks["DQ_SCHEMA_REQUIRED_COLUMNS"].status == "FAIL"
    assert "units" in checks["DQ_SCHEMA_REQUIRED_COLUMNS"].details


def test_inconsistent_value_representation_fails_value_state_check(
    bronze_dataframe_factory,
) -> None:
    silver = _silver(bronze_dataframe_factory({"Value": "C"})).withColumn(
        "value_status", F.lit(None).cast("string")
    )

    report = assess_silver_quality(silver, generated_at=REPORT_TIME)

    assert _checks(report)["DQ_VALIDITY_VALUE_STATE"].affected_rows == 1
    assert report.overall_result == "FAIL"
