"""Shared fixtures for Spark-backed Bronze tests."""

from __future__ import annotations

import pytest

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
