"""Spark-independent contracts for analytical repository implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from nz_industry_benchmarking.api.records import (
    BenchmarkRecord,
    IndustryRecord,
    MetricRecord,
)
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest


class AnalyticsRepository(Protocol):
    """Minimal read contract required by the HTTP service."""

    def list_industries(
        self, *, year: int | None, aggregation_level: str | None
    ) -> Sequence[IndustryRecord]: ...

    def get_metrics(
        self, *, industry_code: str, year: int, aggregation_level: str
    ) -> Sequence[MetricRecord]: ...

    def get_trend(
        self,
        *,
        industry_code: str,
        metric_id: str,
        aggregation_level: str,
        start_year: int | None,
        end_year: int | None,
    ) -> Sequence[MetricRecord]: ...

    def get_benchmarks(
        self, request: BenchmarkRequest
    ) -> Sequence[BenchmarkRecord]: ...
