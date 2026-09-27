"""Typed, validated Silver representation of Bronze AES observations."""

from typing import TYPE_CHECKING, Any

from nz_industry_benchmarking.silver.config import SilverConfig

if TYPE_CHECKING:
    from nz_industry_benchmarking.silver.service import process_silver

__all__ = ["SilverConfig", "process_silver"]


def __getattr__(name: str) -> Any:
    """Load the Spark-backed Silver service export only when requested."""
    if name == "process_silver":
        from nz_industry_benchmarking.silver.service import process_silver

        return process_silver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
