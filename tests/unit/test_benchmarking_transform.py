"""Unit coverage for the three Phase 8 ranking concepts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest
from nz_industry_benchmarking.benchmarking.transform import rank_change_metrics

GOLD_BENCHMARK_SCHEMA = """
    metric_record_id string,
    year int,
    industry_aggregation_nzsioc string,
    industry_code_nzsioc string,
    industry_name_nzsioc string,
    metric_id string,
    metric_name string,
    metric_value decimal(38,18),
    metric_unit string,
    metric_status string,
    source_silver_record_ids array<string>,
    source_ingestion_ids array<string>,
    source_sha256s array<string>,
    silver_input_fingerprints array<string>,
    gold_schema_version string,
    gold_input_fingerprint string,
    gold_processing_timestamp timestamp
"""


@pytest.fixture
def gold_factory(spark):
    """Build the minimal contract-shaped Gold input for ranking tests."""

    def build(*overrides: dict[str, object]):
        base = {
            "metric_record_id": "record-AA",
            "year": 2025,
            "industry_aggregation_nzsioc": "Level 1",
            "industry_code_nzsioc": "AA",
            "industry_name_nzsioc": "Industry AA",
            "metric_id": "M4",
            "metric_name": "Total income year-over-year growth",
            "metric_value": Decimal("1"),
            "metric_unit": "Percent change",
            "metric_status": "PUBLISHED",
            "source_silver_record_ids": ["silver-AA"],
            "source_ingestion_ids": ["ingestion-1"],
            "source_sha256s": ["A" * 64],
            "silver_input_fingerprints": ["silver-fingerprint"],
            "gold_schema_version": "aes-gold-metrics-v1",
            "gold_input_fingerprint": "gold-fingerprint",
            "gold_processing_timestamp": datetime(2026, 9, 24, 1, 2, 3),
        }
        return spark.createDataFrame(
            [{**base, **override} for override in overrides],
            GOLD_BENCHMARK_SCHEMA,
        )

    return build


def _row(code: str, value: str, **overrides: object) -> dict[str, object]:
    return {
        "metric_record_id": f"record-{code}",
        "industry_code_nzsioc": code,
        "industry_name_nzsioc": f"Industry {code}",
        "metric_value": Decimal(value),
        **overrides,
    }


def test_ranking_concepts_order_and_preserve_signed_values(gold_factory) -> None:
    gold = gold_factory(
        _row("A", "10"),
        _row("B", "5"),
        _row("C", "-2"),
        _row("D", "-10"),
        _row("E", "0"),
        _row("F", "10"),
        _row("X", "999", metric_status="CONFIDENTIAL"),
    )

    increases = rank_change_metrics(
        gold, ranking_type="top_increases", top_n=10
    ).orderBy("rank_position")
    decreases = rank_change_metrics(
        gold, ranking_type="top_decreases", top_n=10
    ).orderBy("rank_position")
    movements = rank_change_metrics(
        gold, ranking_type="largest_movements", top_n=10
    ).orderBy("rank_position")

    increase_values = [
        (row.industry_code_nzsioc, row.metric_value) for row in increases.collect()
    ]
    decrease_values = [
        (row.industry_code_nzsioc, row.metric_value) for row in decreases.collect()
    ]
    movement_values = [
        (row.industry_code_nzsioc, row.metric_value) for row in movements.collect()
    ]

    assert increase_values == [
        ("A", Decimal("10")),
        ("F", Decimal("10")),
        ("B", Decimal("5")),
    ]
    assert decrease_values == [
        ("D", Decimal("-10")),
        ("C", Decimal("-2")),
    ]
    assert movement_values == [
        ("A", Decimal("10")),
        ("D", Decimal("-10")),
        ("F", Decimal("10")),
        ("B", Decimal("5")),
        ("C", Decimal("-2")),
        ("E", Decimal("0")),
    ]
    assert {row.metric_unit for row in movements.collect()} == {"Percent change"}


def test_rankings_are_partitioned_by_year_metric_and_level(gold_factory) -> None:
    gold = gold_factory(
        _row("L1", "1"),
        _row("L3", "2", industry_aggregation_nzsioc="Level 3"),
        _row("L4", "2.5", industry_aggregation_nzsioc="Level 4"),
        _row("M5", "3", metric_id="M5", metric_unit="NZD millions change"),
        _row("M6", "3", metric_id="M6", metric_unit="Percentage points"),
        _row("Y24", "4", year=2024),
    )

    rows = rank_change_metrics(
        gold, ranking_type="top_increases", top_n=1
    ).collect()

    assert len(rows) == 6
    assert {row.rank_position for row in rows} == {1}
    assert {
        (row.year, row.metric_id, row.industry_aggregation_nzsioc)
        for row in rows
    } == {
        (2025, "M4", "Level 1"),
        (2025, "M4", "Level 3"),
        (2025, "M4", "Level 4"),
        (2025, "M5", "Level 1"),
        (2025, "M6", "Level 1"),
        (2024, "M4", "Level 1"),
    }


def test_top_n_can_exceed_eligible_rows_and_empty_results_are_valid(
    gold_factory,
) -> None:
    gold = gold_factory(_row("A", "2"), _row("B", "1"))

    assert rank_change_metrics(
        gold, ranking_type="top_increases", top_n=50
    ).count() == 2
    assert rank_change_metrics(
        gold, ranking_type="top_decreases", top_n=50
    ).count() == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [("metric_id", "M1"), ("ranking_type", "unknown"), ("top_n", 0)],
)
def test_request_rejects_unsupported_values(field: str, value: object) -> None:
    arguments = {
        "year": 2025,
        "metric_id": "M4",
        "aggregation_level": "Level 1",
        "ranking_type": "top_increases",
        "top_n": 5,
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        BenchmarkRequest(**arguments)
