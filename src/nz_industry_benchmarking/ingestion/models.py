"""Data structures shared by the ingestion components."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

EXPECTED_COLUMNS = (
    "Year",
    "Industry_aggregation_NZSIOC",
    "Industry_code_NZSIOC",
    "Industry_name_NZSIOC",
    "Units",
    "Variable_code",
    "Variable_name",
    "Variable_category",
    "Value",
    "Industry_code_ANZSIC06",
)

RawRow = dict[str, str]


@dataclass(frozen=True, slots=True)
class RawDataset:
    """AES rows as source strings, plus artifact-level information."""

    columns: tuple[str, ...]
    rows: tuple[RawRow, ...]
    source_sha256: str

    @property
    def row_count(self) -> int:
        """Return the number of source data rows, excluding the header."""
        return len(self.rows)


@dataclass(frozen=True, slots=True)
class IngestionMetadata:
    """Metadata persisted once for a logical source-artifact ingestion."""

    ingestion_id: str
    source_file: str
    source_url: str
    source_sha256: str
    dataset_year: int
    dataset_version: str
    ingestion_timestamp: str
    row_count: int
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable metadata record."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> IngestionMetadata:
        """Recreate metadata from a manifest record."""
        return cls(
            ingestion_id=str(value["ingestion_id"]),
            source_file=str(value["source_file"]),
            source_url=str(value["source_url"]),
            source_sha256=str(value["source_sha256"]),
            dataset_year=int(value["dataset_year"]),
            dataset_version=str(value["dataset_version"]),
            ingestion_timestamp=str(value["ingestion_timestamp"]),
            row_count=int(value["row_count"]),
            schema_version=str(value["schema_version"]),
        )


@dataclass(frozen=True, slots=True)
class IngestionOutcome:
    """Result returned by an ingestion attempt."""

    metadata: IngestionMetadata
    duplicate: bool
    dataset: RawDataset

    def summary(self) -> dict[str, Any]:
        """Return a compact result that intentionally excludes source rows."""
        return {
            "status": "duplicate" if self.duplicate else "ingested",
            "metadata": self.metadata.to_dict(),
        }
