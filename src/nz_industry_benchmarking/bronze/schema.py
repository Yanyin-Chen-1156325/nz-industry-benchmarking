"""Explicit, string-preserving schema for the Bronze AES table."""

from __future__ import annotations

from datetime import UTC, datetime

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from nz_industry_benchmarking.ingestion.models import (
    EXPECTED_COLUMNS,
    IngestionOutcome,
)

BRONZE_METADATA_COLUMNS = (
    "ingestion_id",
    "source_file",
    "source_url",
    "source_sha256",
    "dataset_year",
    "dataset_version",
    "ingestion_timestamp",
    "row_count",
    "schema_version",
    "source_row_number",
)

BRONZE_SCHEMA = StructType(
    [StructField(column, StringType(), nullable=False) for column in EXPECTED_COLUMNS]
    + [
        StructField("ingestion_id", StringType(), nullable=False),
        StructField("source_file", StringType(), nullable=False),
        StructField("source_url", StringType(), nullable=False),
        StructField("source_sha256", StringType(), nullable=False),
        StructField("dataset_year", IntegerType(), nullable=False),
        StructField("dataset_version", StringType(), nullable=False),
        StructField("ingestion_timestamp", TimestampType(), nullable=False),
        StructField("row_count", LongType(), nullable=False),
        StructField("schema_version", StringType(), nullable=False),
        StructField("source_row_number", LongType(), nullable=False),
    ]
)


def build_bronze_dataframe(
    spark: SparkSession,
    outcome: IngestionOutcome,
) -> DataFrame:
    """Attach lineage fields without changing any raw source field."""
    if outcome.dataset.columns != EXPECTED_COLUMNS:
        raise ValueError(
            "Ingestion output columns do not match the AES source contract."
        )
    if outcome.dataset.row_count != outcome.metadata.row_count:
        raise ValueError("Ingestion row count does not match its captured metadata.")

    metadata = outcome.metadata
    timestamp = _parse_utc_timestamp(metadata.ingestion_timestamp)
    records = [
        tuple(row[column] for column in EXPECTED_COLUMNS)
        + (
            metadata.ingestion_id,
            metadata.source_file,
            metadata.source_url,
            metadata.source_sha256,
            metadata.dataset_year,
            metadata.dataset_version,
            timestamp,
            metadata.row_count,
            metadata.schema_version,
            source_row_number,
        )
        for source_row_number, row in enumerate(outcome.dataset.rows, start=1)
    ]
    return spark.createDataFrame(records, schema=BRONZE_SCHEMA)


def _parse_utc_timestamp(value: str) -> datetime:
    """Parse the Phase 3 ISO-8601 timestamp for Spark's timestamp type."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid ingestion timestamp: {value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Ingestion timestamp must include a UTC offset.")
    return parsed.astimezone(UTC).replace(tzinfo=None)
