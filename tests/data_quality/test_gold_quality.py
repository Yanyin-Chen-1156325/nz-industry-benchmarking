"""Data-contract checks for Gold metric output."""

from __future__ import annotations

from datetime import UTC, datetime

from pyspark.sql import functions as F

from nz_industry_benchmarking.gold.contract import GOLD_STATUSES, METRIC_IDS
from nz_industry_benchmarking.gold.transform import transform_silver_to_gold
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def test_gold_grain_values_and_lineage_are_consistent(
    bronze_dataframe_factory,
) -> None:
    timestamp = datetime(2026, 9, 24, tzinfo=UTC)
    bronze = bronze_dataframe_factory(
        {},
        {
            "Year": "2024",
            "Value": "100",
            "Industry_aggregation_NZSIOC": "Level 3",
        },
    )
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint="GOLD-QUALITY-SILVER",
        processing_timestamp=timestamp,
    )
    gold = transform_silver_to_gold(
        silver,
        input_fingerprint="GOLD-QUALITY-INPUT",
        processing_timestamp=timestamp,
    )

    assert gold.count() == 12
    assert gold.select(
        "year",
        "industry_aggregation_nzsioc",
        "industry_code_nzsioc",
        "metric_id",
    ).distinct().count() == 12
    assert {row.metric_id for row in gold.select("metric_id").distinct().collect()} == (
        set(METRIC_IDS)
    )
    assert gold.where(~F.col("metric_status").isin(*GOLD_STATUSES)).count() == 0
    assert gold.where(
        (F.col("metric_status") == "PUBLISHED") & F.col("metric_value").isNull()
    ).count() == 0
    assert gold.where(
        (F.col("metric_status") != "PUBLISHED") & F.col("metric_value").isNotNull()
    ).count() == 0
    assert gold.where(F.size("silver_input_fingerprints") == 0).count() == 0
