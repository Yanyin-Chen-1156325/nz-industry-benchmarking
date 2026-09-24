"""Request model for one bounded benchmark query."""

from __future__ import annotations

from dataclasses import dataclass

from nz_industry_benchmarking.benchmarking.contract import (
    CHANGE_METRIC_IDS,
    RANKING_TYPES,
)


@dataclass(frozen=True, slots=True)
class BenchmarkRequest:
    """Select one year/metric/aggregation ranking for future API use."""

    year: int
    metric_id: str
    aggregation_level: str
    ranking_type: str
    top_n: int = 10

    def __post_init__(self) -> None:
        if self.metric_id not in CHANGE_METRIC_IDS:
            raise ValueError(
                f"metric_id must be one of {CHANGE_METRIC_IDS}; got {self.metric_id!r}."
            )
        if self.ranking_type not in RANKING_TYPES:
            raise ValueError(
                "ranking_type must be one of "
                f"{RANKING_TYPES}; got {self.ranking_type!r}."
            )
        if not self.aggregation_level.strip():
            raise ValueError("aggregation_level must not be blank.")
        if self.top_n < 1:
            raise ValueError("top_n must be at least 1.")
