"""Data-quality checks for Silver validation outcomes."""

from __future__ import annotations

from datetime import UTC, datetime

from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def transform(dataframe):
    return transform_bronze_to_silver(
        dataframe,
        input_fingerprint="QUALITY-TEST",
        processing_timestamp=datetime(2026, 9, 24, tzinfo=UTC),
    )


def test_duplicate_observations_are_retained_and_flagged(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory({}, {})

    rows = transform(bronze).orderBy("source_row_number").collect()

    assert len(rows) == 2
    assert all(not row.is_valid for row in rows)
    assert all("OBSERVATION_DUPLICATE" in row.validation_rule_ids for row in rows)


def test_unexpected_variable_metadata_is_invalid_not_standardized(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {"Variable_name": "Invented total income label"}
    )

    row = transform(bronze).first()

    assert row.variable_name == "Invented total income label"
    assert row.record_status == "INVALID"
    assert "VARIABLE_DEFINITION_UNEXPECTED" in row.validation_rule_ids


def test_aggregation_level_is_part_of_observation_identity(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {},
        {"Industry_aggregation_NZSIOC": "Level 3"},
    )

    rows = transform(bronze).collect()

    assert len(rows) == 2
    assert all("OBSERVATION_DUPLICATE" not in row.validation_rule_ids for row in rows)
