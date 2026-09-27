"""Application/query service independent from FastAPI and Spark details."""

from __future__ import annotations

from nz_industry_benchmarking.api.errors import NoMatchingDataError
from nz_industry_benchmarking.api.models import (
    BenchmarkItem,
    BenchmarkResponse,
    Industry,
    IndustryListResponse,
    IndustryPerformanceResponse,
    IndustryTrendResponse,
    MetricLineage,
    MetricObservation,
)
from nz_industry_benchmarking.api.protocols import AnalyticsRepository
from nz_industry_benchmarking.api.records import BenchmarkRecord, MetricRecord
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest


class AnalyticsService:
    """Return public response models from an injected analytical repository."""

    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    def list_industries(
        self, *, year: int | None, aggregation_level: str | None
    ) -> IndustryListResponse:
        records = self._repository.list_industries(
            year=year, aggregation_level=aggregation_level
        )
        if not records:
            raise NoMatchingDataError("No industries matched the query.")
        industries = [
            Industry(
                industry_code=record.industry_code,
                industry_name=record.industry_name,
                aggregation_level=record.aggregation_level,
                available_years=list(record.available_years),
            )
            for record in records
        ]
        return IndustryListResponse(count=len(industries), industries=industries)

    def get_performance(
        self, *, industry_code: str, year: int, aggregation_level: str
    ) -> IndustryPerformanceResponse:
        records = self._repository.get_metrics(
            industry_code=industry_code.upper(),
            year=year,
            aggregation_level=aggregation_level,
        )
        if not records:
            raise NoMatchingDataError("No performance data matched the query.")
        metrics = [_metric_observation(record) for record in records]
        first = records[0]
        return IndustryPerformanceResponse(
            industry_code=first.industry_code,
            industry_name=first.industry_name,
            aggregation_level=first.aggregation_level,
            year=year,
            metrics=metrics,
        )

    def get_trend(
        self,
        *,
        industry_code: str,
        metric_id: str,
        aggregation_level: str,
        start_year: int | None,
        end_year: int | None,
    ) -> IndustryTrendResponse:
        if start_year is not None and end_year is not None and start_year > end_year:
            raise ValueError("start_year must be less than or equal to end_year.")
        records = self._repository.get_trend(
            industry_code=industry_code.upper(),
            metric_id=metric_id,
            aggregation_level=aggregation_level,
            start_year=start_year,
            end_year=end_year,
        )
        if not records:
            raise NoMatchingDataError("No trend data matched the query.")
        observations = [_metric_observation(record) for record in records]
        first = records[0]
        return IndustryTrendResponse(
            industry_code=first.industry_code,
            industry_name=first.industry_name,
            aggregation_level=first.aggregation_level,
            metric_id=metric_id,
            observations=observations,
        )

    def get_benchmarks(
        self,
        *,
        year: int,
        metric_id: str,
        aggregation_level: str,
        ranking_type: str,
        top_n: int,
    ) -> BenchmarkResponse:
        request = BenchmarkRequest(
            year=year,
            metric_id=metric_id,
            aggregation_level=aggregation_level,
            ranking_type=ranking_type,
            top_n=top_n,
        )
        records = self._repository.get_benchmarks(request)
        if not records:
            raise NoMatchingDataError("No published benchmark data matched the query.")
        results = [_benchmark_item(record) for record in records]
        return BenchmarkResponse(
            year=year,
            metric_id=metric_id,
            aggregation_level=aggregation_level,
            ranking_type=ranking_type,
            requested_top_n=top_n,
            count=len(results),
            results=results,
        )


def _metric_observation(record: MetricRecord) -> MetricObservation:
    value = float(record.metric_value) if record.metric_value is not None else None
    if record.metric_status != "PUBLISHED":
        value = None
    return MetricObservation(
        year=record.year,
        industry_code=record.industry_code,
        industry_name=record.industry_name,
        aggregation_level=record.aggregation_level,
        metric_id=record.metric_id,
        metric_name=record.metric_name,
        metric_value=value,
        metric_status=record.metric_status,
        metric_unit=record.metric_unit,
        current_input_status=record.current_input_status,
        prior_input_status=record.prior_input_status,
        lineage=_metric_lineage(record),
    )


def _benchmark_item(record: BenchmarkRecord) -> BenchmarkItem:
    return BenchmarkItem(
        rank_position=record.rank_position,
        ranking_type=record.ranking_type,
        year=record.year,
        industry_code=record.industry_code,
        industry_name=record.industry_name,
        aggregation_level=record.aggregation_level,
        metric_id=record.metric_id,
        metric_name=record.metric_name,
        metric_value=float(record.metric_value),
        absolute_metric_value=float(record.absolute_metric_value),
        metric_status="PUBLISHED",
        metric_unit=record.metric_unit,
        lineage=MetricLineage(
            metric_record_id=record.metric_record_id,
            source_silver_record_ids=list(record.source_silver_record_ids),
            source_ingestion_ids=list(record.source_ingestion_ids),
            source_sha256s=list(record.source_sha256s),
            gold_input_fingerprint=record.gold_input_fingerprint,
        ),
    )


def _metric_lineage(record: MetricRecord) -> MetricLineage:
    return MetricLineage(
        metric_record_id=record.metric_record_id,
        source_silver_record_ids=list(record.source_silver_record_ids),
        source_ingestion_ids=list(record.source_ingestion_ids),
        source_sha256s=list(record.source_sha256s),
        gold_input_fingerprint=record.gold_input_fingerprint,
    )
