"""Framework-independent records returned by the analytical repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class IndustryRecord:
    """One available industry within one NZSIOC aggregation level."""

    industry_code: str
    industry_name: str
    aggregation_level: str
    available_years: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MetricRecord:
    """One existing Gold metric observation and its traceability fields."""

    metric_record_id: str
    year: int
    aggregation_level: str
    industry_code: str
    industry_name: str
    metric_id: str
    metric_name: str
    metric_value: Decimal | None
    metric_status: str
    metric_unit: str
    current_input_status: str | None
    prior_input_status: str | None
    source_silver_record_ids: tuple[str, ...]
    source_ingestion_ids: tuple[str, ...]
    source_sha256s: tuple[str, ...]
    gold_input_fingerprint: str


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    """One ranked Phase 8 result with its original signed Gold value."""

    ranking_type: str
    rank_position: int
    year: int
    aggregation_level: str
    metric_id: str
    metric_name: str
    metric_value: Decimal
    absolute_metric_value: Decimal
    metric_status: str
    metric_unit: str
    industry_code: str
    industry_name: str
    metric_record_id: str
    source_silver_record_ids: tuple[str, ...]
    source_ingestion_ids: tuple[str, ...]
    source_sha256s: tuple[str, ...]
    gold_input_fingerprint: str
    gold_processing_timestamp: datetime
