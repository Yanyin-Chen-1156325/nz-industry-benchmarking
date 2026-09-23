"""Faithful Delta persistence for ingested AES source data."""

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.bronze.service import persist_ingestion

__all__ = ["BronzeConfig", "persist_ingestion"]
