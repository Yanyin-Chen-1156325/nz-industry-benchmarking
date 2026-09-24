"""Typed public request and response contracts for the REST API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MetricId = Literal["M1", "M2", "M3", "M4", "M5", "M6"]
ChangeMetricId = Literal["M4", "M5", "M6"]
AggregationLevel = Literal["Level 1", "Level 3", "Level 4"]
RankingType = Literal["top_increases", "top_decreases", "largest_movements"]


class ApiModel(BaseModel):
    """Base response model with a stable strict schema."""

    model_config = ConfigDict(extra="forbid")


class ErrorDetail(ApiModel):
    """One safe validation detail."""

    field: str
    message: str


class ErrorContent(ApiModel):
    """Consistent error payload content."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(ApiModel):
    """Envelope used by all API errors."""

    error: ErrorContent


class HealthResponse(ApiModel):
    """Minimal process health response."""

    status: Literal["ok"] = "ok"


class Industry(ApiModel):
    """An industry available in Gold analytics."""

    industry_code: str
    industry_name: str
    aggregation_level: AggregationLevel
    available_years: list[int]


class IndustryListResponse(ApiModel):
    """Bounded metadata response for available industries."""

    count: int
    industries: list[Industry]


class MetricLineage(ApiModel):
    """Identifiers sufficient to trace an API value into Gold and upstream."""

    metric_record_id: str
    source_silver_record_ids: list[str]
    source_ingestion_ids: list[str]
    source_sha256s: list[str]
    gold_input_fingerprint: str


class MetricObservation(ApiModel):
    """One approved Gold observation; unavailable values remain null."""

    year: int
    industry_code: str
    industry_name: str
    aggregation_level: AggregationLevel
    metric_id: MetricId
    metric_name: str
    metric_value: float | None
    metric_status: str
    metric_unit: str
    current_input_status: str | None
    prior_input_status: str | None
    lineage: MetricLineage


class IndustryPerformanceResponse(ApiModel):
    """All existing M1-M6 observations for one industry and year."""

    industry_code: str
    industry_name: str
    aggregation_level: AggregationLevel
    year: int
    metrics: list[MetricObservation]


class IndustryTrendResponse(ApiModel):
    """Chronological existing Gold observations for one industry/metric."""

    industry_code: str
    industry_name: str
    aggregation_level: AggregationLevel
    metric_id: MetricId
    observations: list[MetricObservation]


class BenchmarkItem(ApiModel):
    """One ranked published change metric."""

    rank_position: int
    ranking_type: RankingType
    year: int
    industry_code: str
    industry_name: str
    aggregation_level: AggregationLevel
    metric_id: ChangeMetricId
    metric_name: str
    metric_value: float
    absolute_metric_value: float
    metric_status: Literal["PUBLISHED"]
    metric_unit: str
    lineage: MetricLineage


class BenchmarkResponse(ApiModel):
    """One bounded ranking partition."""

    year: int
    metric_id: ChangeMetricId
    aggregation_level: AggregationLevel
    ranking_type: RankingType
    requested_top_n: int
    count: int
    results: list[BenchmarkItem]
