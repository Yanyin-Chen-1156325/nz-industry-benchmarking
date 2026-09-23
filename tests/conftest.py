"""Shared fixtures for Spark-backed Bronze tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from nz_industry_benchmarking.bronze.schema import BRONZE_SCHEMA
from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.ingestion.models import (
    EXPECTED_COLUMNS,
    IngestionMetadata,
    IngestionOutcome,
    RawDataset,
)


@pytest.fixture
def bronze_outcome() -> IngestionOutcome:
    """Return representative raw records containing protected values."""
    first_values = [
        "2025", "L4", "A", "One", "Count", "X", "Metric", "Cat", "C", "A01"
    ]
    second_values = [
        "2024", "L4", "B", "Two", "Count", "X", "Metric", "Cat", "S", "B01"
    ]
    rows = (
        dict(zip(EXPECTED_COLUMNS, first_values, strict=True)),
        dict(zip(EXPECTED_COLUMNS, second_values, strict=True)),
    )
    metadata = IngestionMetadata(
        ingestion_id="ABC123",
        source_file="data/raw/aes.csv",
        source_url="https://www.stats.govt.nz/aes.csv",
        source_sha256="ABC123",
        dataset_year=2025,
        dataset_version="2025-provisional",
        ingestion_timestamp="2026-09-23T01:02:03Z",
        row_count=2,
        schema_version="aes-public-csv-v1",
    )
    return IngestionOutcome(
        metadata=metadata,
        duplicate=False,
        dataset=RawDataset(
            columns=EXPECTED_COLUMNS,
            rows=rows,
            source_sha256="ABC123",
        ),
    )


@pytest.fixture(scope="session")
def spark():
    """Provide one local Delta-enabled Spark session for the test suite."""
    session = create_spark_session(app_name="nz-industry-benchmarking-tests")
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture
def bronze_dataframe_factory(spark):
    """Build contract-shaped Bronze frames from concise row overrides."""

    def build(*overrides: dict[str, object]):
        row_count = len(overrides)
        source_sha256 = "A" * 64
        base: dict[str, object] = {
            "Year": "2025",
            "Industry_aggregation_NZSIOC": "Level 1",
            "Industry_code_NZSIOC": "AA",
            "Industry_name_NZSIOC": "Agriculture",
            "Units": "Dollars (millions)",
            "Variable_code": "H01",
            "Variable_name": "Total income",
            "Variable_category": "Financial performance",
            "Value": "1,234",
            "Industry_code_ANZSIC06": "ANZSIC06 division A",
            "ingestion_id": source_sha256,
            "source_file": "data/raw/aes.csv",
            "source_url": "https://www.stats.govt.nz/aes.csv",
            "source_sha256": source_sha256,
            "dataset_year": 2025,
            "dataset_version": "2025-financial-year-provisional",
            "ingestion_timestamp": datetime(2026, 9, 23, 1, 2, 3),
            "row_count": row_count,
            "schema_version": "aes-public-csv-v1",
        }
        records = []
        for row_number, values in enumerate(overrides, start=1):
            record = {**base, "source_row_number": row_number, **values}
            records.append(tuple(record[field.name] for field in BRONZE_SCHEMA.fields))
        return spark.createDataFrame(records, BRONZE_SCHEMA)

    return build
