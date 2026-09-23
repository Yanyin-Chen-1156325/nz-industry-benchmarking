"""Unit tests for raw AES CSV loading."""

import csv
from pathlib import Path

import pytest

from nz_industry_benchmarking.ingestion.errors import (
    SourceFileNotFoundError,
    SourceSchemaError,
)
from nz_industry_benchmarking.ingestion.loader import load_raw_csv
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS


def write_csv(path: Path, rows: list[list[str]]) -> None:
    """Write a small source-shaped UTF-8 CSV fixture."""
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(rows)


def source_row(value: str) -> list[str]:
    """Return one complete source row with a caller-supplied raw value."""
    return [
        "2025",
        "Level 1",
        "CC",
        "Manufacturing",
        "Dollars (millions)",
        "H01",
        "Total income",
        "Financial performance",
        value,
        "ANZSIC06 division C",
    ]


def test_load_raw_csv_preserves_source_strings(tmp_path: Path) -> None:
    source = tmp_path / "aes.csv"
    write_csv(source, [source_row("1,234"), source_row("C"), source_row("S")])

    dataset = load_raw_csv(source)

    assert dataset.columns == EXPECTED_COLUMNS
    assert dataset.row_count == 3
    assert [row["Value"] for row in dataset.rows] == ["1,234", "C", "S"]
    assert all(isinstance(value, str) for row in dataset.rows for value in row.values())


def test_load_raw_csv_fails_clearly_when_source_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "missing.csv"

    with pytest.raises(SourceFileNotFoundError, match="does not exist"):
        load_raw_csv(source)


def test_load_raw_csv_rejects_unexpected_header(tmp_path: Path) -> None:
    source = tmp_path / "aes.csv"
    source.write_text("Year,Invented_column\n2025,value\n", encoding="utf-8")

    with pytest.raises(SourceSchemaError, match="Phase 0 contract"):
        load_raw_csv(source)
