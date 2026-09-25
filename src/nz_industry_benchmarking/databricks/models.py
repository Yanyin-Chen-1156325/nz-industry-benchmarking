"""Inspectable result from a Databricks initial pipeline run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.quality.models import QualityReport
from nz_industry_benchmarking.silver.models import SilverWriteResult


@dataclass(frozen=True, slots=True)
class DatabricksInitialLoadResult:
    """Bronze, Silver, quality, and Gold outcomes for manual inspection."""

    bronze: BronzeWriteResult
    silver: SilverWriteResult
    quality: QualityReport
    gold: GoldWriteResult

    def to_dict(self) -> dict[str, Any]:
        """Return a notebook-friendly JSON-compatible summary."""
        return {
            "bronze": self.bronze.to_dict(),
            "silver": self.silver.to_dict(),
            "quality": self.quality.to_dict(),
            "gold": self.gold.to_dict(),
        }
