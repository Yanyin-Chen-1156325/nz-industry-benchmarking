"""Unit-level checks for faithful Bronze row construction."""

from __future__ import annotations

from datetime import datetime

from pyspark.sql.types import StringType

from nz_industry_benchmarking.bronze.schema import (
    BRONZE_METADATA_COLUMNS,
    build_bronze_dataframe,
)
from nz_industry_benchmarking.ingestion.models import (
    EXPECTED_COLUMNS,
    IngestionMetadata,
    IngestionOutcome,
)


def test_bronze_dataframe_preserves_raw_values_and_adds_metadata(
    spark, bronze_outcome
) -> None:
    dataframe = build_bronze_dataframe(spark, bronze_outcome)
    rows = dataframe.orderBy("source_row_number").collect()

    assert dataframe.columns == [*EXPECTED_COLUMNS, *BRONZE_METADATA_COLUMNS]
    assert all(
        isinstance(dataframe.schema[column].dataType, StringType)
        for column in EXPECTED_COLUMNS
    )
    assert [row.Value for row in rows] == ["C", "S"]
    assert [row.source_row_number for row in rows] == [1, 2]
    assert rows[0].ingestion_id == "ABC123"
    assert rows[0].ingestion_timestamp == datetime(2026, 9, 23, 1, 2, 3)
    assert rows[0].row_count == 2


def test_bronze_dataframe_rejects_metadata_row_count_mismatch(
    spark, bronze_outcome
) -> None:
    outcome = bronze_outcome
    invalid = IngestionOutcome(
        metadata=IngestionMetadata(
            ingestion_id=outcome.metadata.ingestion_id,
            source_file=outcome.metadata.source_file,
            source_url=outcome.metadata.source_url,
            source_sha256=outcome.metadata.source_sha256,
            dataset_year=outcome.metadata.dataset_year,
            dataset_version=outcome.metadata.dataset_version,
            ingestion_timestamp=outcome.metadata.ingestion_timestamp,
            row_count=3,
            schema_version=outcome.metadata.schema_version,
        ),
        duplicate=False,
        dataset=outcome.dataset,
    )

    try:
        build_bronze_dataframe(spark, invalid)
    except ValueError as error:
        assert "row count" in str(error)
    else:
        raise AssertionError("Expected mismatched ingestion metadata to be rejected.")
