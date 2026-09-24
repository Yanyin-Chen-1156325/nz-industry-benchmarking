"""Configuration shared by the incremental pipeline stages."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.silver.config import SilverConfig


@dataclass(frozen=True, slots=True)
class IncrementalConfig:
    """Existing layer configurations composed without new dependencies."""

    ingestion: IngestionConfig
    bronze: BronzeConfig
    silver: SilverConfig
    gold: GoldConfig

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> IncrementalConfig:
        """Build the four existing configurations from their environment values."""
        return cls(
            ingestion=IngestionConfig.from_environment(environ),
            bronze=BronzeConfig.from_environment(environ),
            silver=SilverConfig.from_environment(environ),
            gold=GoldConfig.from_environment(environ),
        )
