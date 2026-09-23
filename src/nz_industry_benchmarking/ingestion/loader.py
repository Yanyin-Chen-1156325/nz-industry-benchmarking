"""Raw CSV loading without Silver-layer conversions."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from nz_industry_benchmarking.ingestion.errors import (
    SourceCsvError,
    SourceFileNotFoundError,
    SourceSchemaError,
)
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS, RawDataset


def calculate_sha256(path: Path) -> str:
    """Calculate an uppercase SHA-256 digest from the exact source bytes."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest().upper()


def load_raw_csv(path: Path) -> RawDataset:
    """Load the AES CSV while preserving every source field as text."""
    if not path.is_file():
        raise SourceFileNotFoundError(f"AES source file does not exist: {path}")

    source_sha256 = calculate_sha256(path)

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            actual_columns = tuple(reader.fieldnames or ())
            if actual_columns != EXPECTED_COLUMNS:
                raise SourceSchemaError(
                    "AES source header does not match the Phase 0 contract. "
                    f"Expected {EXPECTED_COLUMNS!r}; received {actual_columns!r}."
                )

            rows = tuple(_read_row(reader, row) for row in reader)
    except UnicodeDecodeError as error:
        raise SourceCsvError(f"AES source is not valid UTF-8: {path}") from error
    except csv.Error as error:
        raise SourceCsvError(f"AES source is not valid CSV: {path}: {error}") from error

    if not rows:
        raise SourceCsvError(f"AES source contains no data rows: {path}")

    return RawDataset(
        columns=actual_columns,
        rows=rows,
        source_sha256=source_sha256,
    )


def _read_row(
    reader: csv.DictReader[str],
    row: dict[str | None, str | None],
) -> dict[str, str]:
    """Reject malformed row shapes without changing valid source strings."""
    if None in row or any(value is None for value in row.values()):
        raise SourceCsvError(f"Malformed CSV row at line {reader.line_num}.")
    return {str(key): value for key, value in row.items() if value is not None}
