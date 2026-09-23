"""Unit tests for typed Silver value handling."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver

PROCESSING_TIME = datetime(2026, 9, 24, 2, 3, 4, tzinfo=UTC)


def transform(dataframe):
    """Apply the deterministic test processing identity."""
    return transform_bronze_to_silver(
        dataframe,
        input_fingerprint="TEST-FINGERPRINT",
        processing_timestamp=PROCESSING_TIME,
    )


def test_value_states_and_negative_numbers_are_preserved(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {"Value": "1,234.5", "Variable_code": "H01"},
        {
            "Value": "-810",
            "Variable_code": "H23",
            "Variable_name": "Surplus before income tax",
        },
        {
            "Value": "C",
            "Variable_code": "H01",
            "Industry_code_NZSIOC": "BB",
        },
        {
            "Value": "S",
            "Variable_code": "H01",
            "Industry_code_NZSIOC": "CC",
        },
    )

    rows = transform(bronze).orderBy("source_row_number").collect()

    assert [row.value_status for row in rows] == [
        "PUBLISHED",
        "PUBLISHED",
        "CONFIDENTIAL",
        "SUPPRESSED",
    ]
    assert rows[0].value_numeric == Decimal("1234.500000000000000000")
    assert rows[1].value_numeric == Decimal("-810.000000000000000000")
    assert rows[2].value_numeric is None
    assert rows[3].value_numeric is None
    assert all(row.is_valid for row in rows)
    assert [row.value_raw for row in rows] == ["1,234.5", "-810", "C", "S"]


def test_unavailable_and_invalid_values_remain_inspectable(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {"Value": " "},
        {"Value": "not-a-number", "Industry_code_NZSIOC": "BB"},
    )

    rows = transform(bronze).orderBy("source_row_number").collect()

    assert len(rows) == 2
    assert rows[0].value_status == "UNAVAILABLE"
    assert rows[0].record_status == "INVALID"
    assert rows[0].validation_rule_ids == ["VALUE_UNAVAILABLE"]
    assert rows[1].value_status == "INVALID"
    assert rows[1].record_status == "INVALID"
    assert rows[1].validation_rule_ids == ["VALUE_INVALID"]


def test_context_dependent_variable_definitions_are_not_collapsed(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        {
            "Variable_code": "H04",
            "Variable_name": "Sales of goods and services",
        },
        {
            "Industry_code_NZSIOC": "BB",
            "Variable_code": "H04",
            "Variable_name": "Sales, government funding, grants and subsidies",
        },
        {
            "Industry_code_NZSIOC": "CC",
            "Variable_code": "H18",
            "Variable_name": "Other Purchases and operating expenses",
        },
        {
            "Industry_code_NZSIOC": "DD",
            "Variable_code": "H18",
            "Variable_name": "Other purchases and operating expenses",
        },
    )

    rows = transform(bronze).collect()

    assert len(rows) == 4
    assert all(row.is_valid for row in rows)
    assert {row.variable_name for row in rows} == {
        "Sales of goods and services",
        "Sales, government funding, grants and subsidies",
        "Other Purchases and operating expenses",
        "Other purchases and operating expenses",
    }
