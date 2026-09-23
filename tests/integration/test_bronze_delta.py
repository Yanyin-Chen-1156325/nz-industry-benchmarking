"""Integration checks for Delta persistence and logical idempotency."""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.bronze.service import persist_ingestion


def test_bronze_delta_write_is_faithful_and_idempotent(
    spark,
    bronze_outcome,
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "bronze" / "aes"
    config = BronzeConfig(table_path=table_path)
    outcome = bronze_outcome

    first = persist_ingestion(spark, outcome, config)
    second = persist_ingestion(spark, outcome, config)
    stored = spark.read.format("delta").load(table_path.resolve().as_uri())

    assert first.duplicate is False
    assert first.inserted_rows == 2
    assert first.total_rows == 2
    assert second.duplicate is True
    assert second.inserted_rows == 0
    assert second.total_rows == 2
    assert stored.count() == 2
    assert {
        row.Value for row in stored.select("Value").collect()
    } == {"C", "S"}
    assert stored.where(F.col("ingestion_id") == "ABC123").count() == 2
    assert stored.select("source_sha256").distinct().first()[0] == "ABC123"
