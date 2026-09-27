"""Faithful Delta persistence for ingested AES source data."""

from typing import TYPE_CHECKING, Any

from nz_industry_benchmarking.bronze.config import BronzeConfig

if TYPE_CHECKING:
    from nz_industry_benchmarking.bronze.service import persist_ingestion

__all__ = ["BronzeConfig", "persist_ingestion"]


def __getattr__(name: str) -> Any:
    """Load the Spark-backed persistence export only when requested."""
    if name == "persist_ingestion":
        from nz_industry_benchmarking.bronze.service import persist_ingestion

        return persist_ingestion
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
