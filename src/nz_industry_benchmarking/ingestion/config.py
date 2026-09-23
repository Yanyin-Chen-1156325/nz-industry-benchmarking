"""Configuration for the AES ingestion command."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOURCE_FILE = Path(
    "data/raw/annual-enterprise-survey-2025-financial-year-provisional.csv"
)
DEFAULT_SOURCE_URL = (
    "https://www.stats.govt.nz/assets/Uploads/Annual-enterprise-survey/"
    "Annual-enterprise-survey-2025-financial-year-provisional/Download-data/"
    "annual-enterprise-survey-2025-financial-year-provisional.csv"
)
DEFAULT_DATASET_YEAR = 2025
DEFAULT_DATASET_VERSION = "2025-financial-year-provisional"
DEFAULT_SCHEMA_VERSION = "aes-public-csv-v1"
DEFAULT_MANIFEST_FILE = Path("data/ingestion/manifest.json")


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    """Runtime settings required to ingest one AES source artifact."""

    source_file: Path = DEFAULT_SOURCE_FILE
    source_url: str = DEFAULT_SOURCE_URL
    dataset_year: int = DEFAULT_DATASET_YEAR
    dataset_version: str = DEFAULT_DATASET_VERSION
    schema_version: str = DEFAULT_SCHEMA_VERSION
    manifest_file: Path = DEFAULT_MANIFEST_FILE

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> IngestionConfig:
        """Build configuration from environment variables with safe defaults."""
        values = os.environ if environ is None else environ
        return cls(
            source_file=Path(values.get("AES_SOURCE_FILE", DEFAULT_SOURCE_FILE)),
            source_url=values.get("AES_SOURCE_URL", DEFAULT_SOURCE_URL),
            dataset_year=int(values.get("AES_DATASET_YEAR", DEFAULT_DATASET_YEAR)),
            dataset_version=values.get("AES_DATASET_VERSION", DEFAULT_DATASET_VERSION),
            schema_version=values.get("AES_SCHEMA_VERSION", DEFAULT_SCHEMA_VERSION),
            manifest_file=Path(
                values.get("AES_INGESTION_MANIFEST", DEFAULT_MANIFEST_FILE)
            ),
        )
