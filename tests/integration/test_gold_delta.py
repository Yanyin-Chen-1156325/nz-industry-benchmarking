"""Integration coverage for Silver-only Gold Delta processing."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.gold.service import process_gold
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def test_gold_processing_is_complete_and_idempotent(
    spark,
    bronze_dataframe_factory,
    tmp_path: Path,
) -> None:
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"
    timestamp = datetime(2026, 9, 24, 1, 2, 3, tzinfo=UTC)
    bronze = bronze_dataframe_factory(
        {"Year": "2024", "Value": "100"},
        {"Year": "2025", "Value": "150"},
    )
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint="GOLD-INTEGRATION-SILVER",
        processing_timestamp=timestamp,
    )
    silver.write.format("delta").save(silver_path.resolve().as_uri())
    config = GoldConfig(silver_path=silver_path, gold_metrics_path=gold_path)

    first = process_gold(spark, config, clock=lambda: timestamp)
    second = process_gold(
        spark,
        config,
        clock=lambda: datetime(2026, 9, 25, 1, 2, 3, tzinfo=UTC),
    )
    stored = spark.read.format("delta").load(gold_path.resolve().as_uri())

    assert first.silver_input_rows == 2
    assert first.gold_output_rows == 12
    assert first.metric_counts == {
        metric_id: 2 for metric_id in "M1 M2 M3 M4 M5 M6".split()
    }
    assert first.duplicate is False
    assert second.duplicate is True
    assert second.gold_output_rows == 12
    assert stored.count() == 12
    assert stored.select("gold_processing_timestamp").distinct().count() == 1
