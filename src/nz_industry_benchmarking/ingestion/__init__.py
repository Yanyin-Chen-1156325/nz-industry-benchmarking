"""Repeatable ingestion for the public Stats NZ AES CSV."""

from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.service import ingest

__all__ = ["IngestionConfig", "ingest"]
