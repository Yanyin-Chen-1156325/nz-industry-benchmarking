"""Reusable industry benchmarking queries over the Gold Delta table."""

from typing import TYPE_CHECKING, Any

from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest

if TYPE_CHECKING:
    from nz_industry_benchmarking.benchmarking.service import query_benchmarks
    from nz_industry_benchmarking.benchmarking.transform import rank_change_metrics

__all__ = ["BenchmarkRequest", "query_benchmarks", "rank_change_metrics"]


def __getattr__(name: str) -> Any:
    """Load Spark-backed convenience exports only when they are requested."""
    if name == "query_benchmarks":
        from nz_industry_benchmarking.benchmarking.service import query_benchmarks

        return query_benchmarks
    if name == "rank_change_metrics":
        from nz_industry_benchmarking.benchmarking.transform import rank_change_metrics

        return rank_change_metrics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
