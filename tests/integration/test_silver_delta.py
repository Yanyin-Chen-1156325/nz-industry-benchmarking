"""Integration tests for Bronze-only Silver processing and persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from nz_industry_benchmarking.silver.config import SilverConfig
from nz_industry_benchmarking.silver.service import process_silver


def test_silver_processing_is_complete_and_idempotent(
    spark,
    bronze_dataframe_factory,
    tmp_path: Path,
) -> None:
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    bronze = bronze_dataframe_factory(
        {},
        {"Industry_code_NZSIOC": "BB", "Value": "C"},
        {"Industry_code_NZSIOC": "CC", "Value": "invalid"},
    )
    bronze.write.format("delta").save(bronze_path.resolve().as_uri())
    config = SilverConfig(bronze_path=bronze_path, silver_path=silver_path)

    first = process_silver(
        spark,
        config,
        clock=lambda: datetime(2026, 9, 24, 1, 2, 3, tzinfo=UTC),
    )
    second = process_silver(
        spark,
        config,
        clock=lambda: datetime(2026, 9, 25, 1, 2, 3, tzinfo=UTC),
    )
    stored = spark.read.format("delta").load(silver_path.resolve().as_uri())

    assert first.bronze_input_rows == 3
    assert first.silver_output_rows == 3
    assert first.valid_rows == 2
    assert first.invalid_rows == 1
    assert first.status_counts == {
        "CONFIDENTIAL": 1,
        "INVALID": 1,
        "PUBLISHED": 1,
    }
    assert first.duplicate is False
    assert second.duplicate is True
    assert second.silver_output_rows == 3
    assert stored.count() == 3
    assert stored.where("record_status = 'INVALID'").count() == 1
    assert stored.select("silver_processing_timestamp").distinct().count() == 1
