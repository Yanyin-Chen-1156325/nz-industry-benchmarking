"""Configuration for the first manual Databricks Bronze-to-Gold load."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.ingestion.config import (
    DEFAULT_DATASET_VERSION,
    DEFAULT_DATASET_YEAR,
    DEFAULT_SCHEMA_VERSION,
    DEFAULT_SOURCE_URL,
    IngestionConfig,
)
from nz_industry_benchmarking.storage import CatalogTableTarget

DEFAULT_CATALOG = "workspace"
DEFAULT_DATABRICKS_SCHEMA = "nz_industry_benchmarking"
DEFAULT_BRONZE_TABLE = "bronze_aes"
DEFAULT_SILVER_TABLE = "silver_aes_observations"
DEFAULT_GOLD_TABLE = "gold_industry_financial_metrics"


@dataclass(frozen=True, slots=True)
class DatabricksInitialLoadConfig:
    """Source metadata and managed-table names for one initial load."""

    source_file: Path
    source_url: str = DEFAULT_SOURCE_URL
    dataset_year: int = DEFAULT_DATASET_YEAR
    dataset_version: str = DEFAULT_DATASET_VERSION
    schema_version: str = DEFAULT_SCHEMA_VERSION
    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_DATABRICKS_SCHEMA
    bronze_table: str = DEFAULT_BRONZE_TABLE
    silver_table: str = DEFAULT_SILVER_TABLE
    gold_table: str = DEFAULT_GOLD_TABLE

    def __post_init__(self) -> None:
        if not isinstance(self.source_file, Path):
            raise TypeError("source_file must be a pathlib.Path.")
        if self.source_file == Path():
            raise ValueError("source_file must not be empty.")
        if not self.source_url.strip():
            raise ValueError("source_url must not be empty.")
        if self.dataset_year < 2000:
            raise ValueError("dataset_year must be 2000 or later.")
        if not self.dataset_version.strip():
            raise ValueError("dataset_version must not be empty.")
        if not self.schema_version.strip():
            raise ValueError("schema_version must not be empty.")
        if len({self.bronze_table, self.silver_table, self.gold_table}) != 3:
            raise ValueError("Bronze, Silver, and Gold table names must be distinct.")
        # Constructing targets here validates all catalog components up front.
        _ = (self.bronze_target, self.silver_target, self.gold_target)

    @property
    def ingestion(self) -> IngestionConfig:
        """Build shared ingestion settings without using its local manifest."""
        return IngestionConfig(
            source_file=self.source_file,
            source_url=self.source_url,
            dataset_year=self.dataset_year,
            dataset_version=self.dataset_version,
            schema_version=self.schema_version,
        )

    @property
    def bronze_target(self) -> CatalogTableTarget:
        return CatalogTableTarget(self.catalog, self.schema, self.bronze_table)

    @property
    def silver_target(self) -> CatalogTableTarget:
        return CatalogTableTarget(self.catalog, self.schema, self.silver_table)

    @property
    def gold_target(self) -> CatalogTableTarget:
        return CatalogTableTarget(self.catalog, self.schema, self.gold_table)
