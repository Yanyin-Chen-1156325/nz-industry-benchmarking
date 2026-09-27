"""Phase 7 Gold analytics for approved AES business metrics."""

from typing import TYPE_CHECKING, Any

from nz_industry_benchmarking.gold.models import GoldWriteResult

if TYPE_CHECKING:
    from nz_industry_benchmarking.gold.service import process_gold

__all__ = ["GoldWriteResult", "process_gold"]


def __getattr__(name: str) -> Any:
    """Load the Spark-backed Gold service export only when requested."""
    if name == "process_gold":
        from nz_industry_benchmarking.gold.service import process_gold

        return process_gold
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
