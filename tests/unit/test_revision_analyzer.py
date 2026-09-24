"""Synthetic classification and current-view tests for Phase 10 revisions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nz_industry_benchmarking.ingestion.models import IngestionMetadata
from nz_industry_benchmarking.revision.analyzer import analyze_revision
from nz_industry_benchmarking.silver.current_view import select_current_bronze_view
from nz_industry_benchmarking.silver.errors import SilverSourceError


def test_revision_classifies_values_metadata_additions_and_absence(
    bronze_dataframe_factory,
) -> None:
    old = bronze_dataframe_factory(
        _old("A", "100"),
        _old("B", "100"),
        _old("C", "100"),
        _old("D", "C"),
        _old("E", "100"),
        _old("F", "S"),
        _old("G", "100"),
        _old("H", "100"),
    )
    incoming = bronze_dataframe_factory(
        _new("A", "100"),
        _new("B", "101"),
        _new("C", "C"),
        _new("D", "100"),
        _new("E", "S"),
        _new("F", "100"),
        _new("G", "100", Industry_name_NZSIOC="Revised industry G"),
        _new("I", "200"),
    )
    metadata = _metadata(2026)

    report = analyze_revision(incoming, old, metadata)

    assert report.overall_result == "ELIGIBLE"
    assert report.overlapping_observations == 7
    assert report.unchanged_republications == 1
    assert report.revised_values == 5
    assert report.revised_metadata == 1
    assert report.newly_added_observations == 1
    assert report.observations_absent_from_incoming == 1
    assert report.current_view_observations_changed == 7
    assert report.value_transition_counts == {
        "CONFIDENTIAL->PUBLISHED": 1,
        "PUBLISHED->CONFIDENTIAL": 1,
        "PUBLISHED->PUBLISHED": 1,
        "PUBLISHED->SUPPRESSED": 1,
        "SUPPRESSED->PUBLISHED": 1,
    }

    current = select_current_bronze_view(old.unionByName(incoming))
    assert current.count() == 9
    assert current.select(
        "Year",
        "Industry_aggregation_NZSIOC",
        "Industry_code_NZSIOC",
        "Variable_code",
    ).distinct().count() == 9
    assert current.where("Industry_code_NZSIOC = 'H'").first().dataset_year == 2025
    assert current.where("Industry_code_NZSIOC = 'B'").first().Value == "101"


def test_equal_dataset_year_is_ambiguous_and_not_ordered_by_version(
    bronze_dataframe_factory,
) -> None:
    old = bronze_dataframe_factory(_old("A", "100"))
    incoming = bronze_dataframe_factory(
        _new("A", "101", dataset_year=2025, dataset_version="final")
    )

    report = analyze_revision(incoming, old, _metadata(2025, version="final"))

    assert report.overall_result == "DEFERRED_AMBIGUOUS"
    assert report.silver_rebuild_required is False
    assert report.gold_rebuild_required is False
    with pytest.raises(SilverSourceError, match="precedence is ambiguous"):
        select_current_bronze_view(old.unionByName(incoming)).count()


def _old(code: str, value: str) -> dict[str, object]:
    return {
        "Year": "2024",
        "Industry_code_NZSIOC": code,
        "Industry_name_NZSIOC": f"Industry {code}",
        "Value": value,
        "ingestion_id": "OLD",
        "source_sha256": "OLD",
        "dataset_year": 2025,
        "dataset_version": "2025-provisional",
        "source_file": "old.csv",
        "ingestion_timestamp": datetime(2026, 6, 1),
    }


def _new(code: str, value: str, **overrides: object) -> dict[str, object]:
    return {
        **_old(code, value),
        "ingestion_id": "NEW",
        "source_sha256": "NEW",
        "dataset_year": 2026,
        "dataset_version": "2026-provisional",
        "source_file": "new.csv",
        "ingestion_timestamp": datetime(2027, 6, 1),
        **overrides,
    }


def _metadata(year: int, *, version: str | None = None) -> IngestionMetadata:
    return IngestionMetadata(
        ingestion_id="NEW",
        source_file="new.csv",
        source_url="https://www.stats.govt.nz/new.csv",
        source_sha256="NEW",
        dataset_year=year,
        dataset_version=version or f"{year}-provisional",
        ingestion_timestamp=datetime(2027, 6, 1, tzinfo=UTC).isoformat(),
        row_count=8,
        schema_version="aes-public-csv-v1",
    )
