"""Unit coverage for the approved M1-M7 Gold metric contract."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from nz_industry_benchmarking.gold.transform import transform_silver_to_gold
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver

PROCESSING_TIME = datetime(2026, 9, 24, 4, 5, 6, tzinfo=UTC)


def _source_row(
    year: int,
    level: str,
    code: str,
    name: str,
    variable: str,
    value: str,
) -> dict[str, object]:
    definitions = {
        "H01": ("Total income", "Financial performance", "Dollars (millions)"),
        "H23": (
            "Surplus before income tax",
            "Financial performance",
            "Dollars (millions)",
        ),
        "H40": ("Return on total assets", "Financial ratios", "Percentage"),
    }
    variable_name, category, units = definitions[variable]
    return {
        "Year": str(year),
        "Industry_aggregation_NZSIOC": level,
        "Industry_code_NZSIOC": code,
        "Industry_name_NZSIOC": name,
        "Variable_code": variable,
        "Variable_name": variable_name,
        "Variable_category": category,
        "Units": units,
        "Value": value,
        "Industry_code_ANZSIC06": f"ANZSIC06 {code}",
    }


def _gold(bronze):
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint="GOLD-UNIT-SILVER",
        processing_timestamp=PROCESSING_TIME,
    )
    return transform_silver_to_gold(
        silver,
        input_fingerprint="GOLD-UNIT-INPUT",
        processing_timestamp=PROCESSING_TIME,
    )


def _metric(gold, year: int, level: str, code: str, metric_id: str):
    return gold.where(
        (gold.year == year)
        & (gold.industry_aggregation_nzsioc == level)
        & (gold.industry_code_nzsioc == code)
        & (gold.metric_id == metric_id)
    ).first()


def test_phase_1_acceptance_examples_are_executable(
    bronze_dataframe_factory,
) -> None:
    bronze = bronze_dataframe_factory(
        _source_row(2024, "Level 1", "CC", "Manufacturing", "H01", "127567"),
        _source_row(2025, "Level 1", "CC", "Manufacturing", "H01", "134105"),
        _source_row(2024, "Level 1", "EE", "Construction", "H23", "8216"),
        _source_row(2025, "Level 1", "EE", "Construction", "H23", "6410"),
        _source_row(2024, "Level 1", "EE", "Construction", "H40", "12"),
        _source_row(2025, "Level 1", "EE", "Construction", "H40", "9"),
        _source_row(2022, "Level 4", "CC521", "Basic Chemical", "H23", "10"),
        _source_row(2023, "Level 4", "CC521", "Basic Chemical", "H23", "C"),
    )
    gold = _gold(bronze)

    m1 = _metric(gold, 2025, "Level 1", "CC", "M1")
    m2 = _metric(gold, 2025, "Level 1", "EE", "M2")
    m3 = _metric(gold, 2025, "Level 1", "EE", "M3")
    m4 = _metric(gold, 2025, "Level 1", "CC", "M4")
    m5 = _metric(gold, 2025, "Level 1", "EE", "M5")
    m6 = _metric(gold, 2025, "Level 1", "EE", "M6")
    protected = _metric(gold, 2023, "Level 4", "CC521", "M2")
    protected_derived = _metric(gold, 2023, "Level 4", "CC521", "M5")

    assert m1.metric_value == Decimal("134105.000000000000000000")
    assert m2.metric_value == Decimal("6410.000000000000000000")
    assert m3.metric_value == Decimal("9.000000000000000000")
    assert m4.metric_value.quantize(Decimal("0.01")) == Decimal("5.13")
    assert m5.metric_value == Decimal("-1806.000000000000000000")
    assert m6.metric_value == Decimal("-3.000000000000000000")
    assert protected.metric_value is None
    assert protected.metric_status == "CONFIDENTIAL"
    assert protected_derived.metric_value is None
    assert protected_derived.metric_status == "UNAVAILABLE_INPUT"
    assert protected_derived.current_input_status == "CONFIDENTIAL"
    assert protected_derived.prior_input_status == "PUBLISHED"


def test_edge_statuses_and_year_rules_are_preserved(
    bronze_dataframe_factory,
) -> None:
    rows = [
        _source_row(2024, "Level 1", "C1", "Confidential", "H23", "5"),
        _source_row(2025, "Level 1", "C1", "Confidential", "H23", "C"),
        _source_row(2025, "Level 1", "S1", "Suppressed", "H40", "S"),
        _source_row(2025, "Level 1", "U1", "Unavailable", "H01", " "),
        _source_row(2025, "Level 1", "I1", "Invalid", "H23", "bad"),
        _source_row(2025, "Level 1", "D1", "Duplicate", "H40", "1"),
        _source_row(2025, "Level 1", "D1", "Duplicate", "H40", "2"),
        _source_row(2025, "Level 1", "N1", "Negative", "H23", "-10"),
        _source_row(2024, "Level 1", "Z1", "Zero base", "H01", "0"),
        _source_row(2025, "Level 1", "Z1", "Zero base", "H01", "10"),
        _source_row(2024, "Level 1", "NB", "Negative base", "H01", "-10"),
        _source_row(2025, "Level 1", "NB", "Negative base", "H01", "10"),
        _source_row(2023, "Level 1", "G1", "Gap", "H01", "10"),
        _source_row(2025, "Level 1", "G1", "Gap", "H01", "20"),
        _source_row(2024, "Level 1", "SEP", "Separate", "H01", "100"),
        _source_row(2025, "Level 1", "SEP", "Separate", "H01", "200"),
        _source_row(2024, "Level 3", "SEP", "Separate", "H01", "200"),
        _source_row(2025, "Level 3", "SEP", "Separate", "H01", "300"),
    ]
    gold = _gold(bronze_dataframe_factory(*rows))

    assert _metric(gold, 2025, "Level 1", "C1", "M2").metric_status == (
        "CONFIDENTIAL"
    )
    assert _metric(gold, 2025, "Level 1", "C1", "M5").metric_status == (
        "UNAVAILABLE_INPUT"
    )
    assert _metric(gold, 2025, "Level 1", "S1", "M3").metric_status == "SUPPRESSED"
    assert _metric(gold, 2025, "Level 1", "U1", "M1").metric_status == "UNAVAILABLE"
    assert _metric(gold, 2025, "Level 1", "I1", "M2").metric_status == "INVALID_VALUE"
    assert _metric(gold, 2025, "Level 1", "D1", "M3").metric_status == (
        "INVALID_DUPLICATE"
    )
    negative = _metric(gold, 2025, "Level 1", "N1", "M2")
    assert negative.metric_status == "PUBLISHED"
    assert negative.metric_value == Decimal("-10.000000000000000000")
    assert _metric(gold, 2025, "Level 1", "Z1", "M4").metric_status == (
        "NOT_MEANINGFUL_BASE"
    )
    assert _metric(gold, 2025, "Level 1", "NB", "M4").metric_status == (
        "NOT_MEANINGFUL_BASE"
    )
    gap = _metric(gold, 2025, "Level 1", "G1", "M4")
    assert gap.metric_status == "UNAVAILABLE_INPUT"
    assert gap.prior_input_status == "UNAVAILABLE"
    level_1 = _metric(gold, 2025, "Level 1", "SEP", "M4")
    level_3 = _metric(gold, 2025, "Level 3", "SEP", "M4")
    assert level_1.metric_value == Decimal("100.000000000000000000")
    assert level_3.metric_value == Decimal("50.000000000000000000")
