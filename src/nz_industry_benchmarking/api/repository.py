"""Gold/benchmark query boundary used by the HTTP application service."""

from __future__ import annotations

from collections.abc import Sequence

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.api.errors import AnalyticalStorageError
from nz_industry_benchmarking.api.protocols import AnalyticsRepository
from nz_industry_benchmarking.api.records import (
    BenchmarkRecord,
    IndustryRecord,
    MetricRecord,
)
from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.benchmarking.errors import BenchmarkError
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest
from nz_industry_benchmarking.benchmarking.service import query_benchmarks
from nz_industry_benchmarking.benchmarking.transform import (
    validate_gold_benchmark_schema,
)

__all__ = ["AnalyticsRepository", "SparkGoldRepository"]


class SparkGoldRepository:
    """Read the current Gold Delta table using one shared Spark session."""

    def __init__(self, spark: SparkSession, config: BenchmarkConfig) -> None:
        self._spark = spark
        self._config = config

    def list_industries(
        self, *, year: int | None, aggregation_level: str | None
    ) -> Sequence[IndustryRecord]:
        """Return distinct industries with their available Gold years."""
        try:
            gold = self._load_gold()
            if year is not None:
                gold = gold.where(F.col("year") == year)
            if aggregation_level is not None:
                gold = gold.where(
                    F.col("industry_aggregation_nzsioc") == aggregation_level
                )
            rows = (
                gold.groupBy(
                    "industry_code_nzsioc",
                    "industry_name_nzsioc",
                    "industry_aggregation_nzsioc",
                )
                .agg(F.sort_array(F.collect_set("year")).alias("available_years"))
                .orderBy(
                    "industry_aggregation_nzsioc",
                    "industry_code_nzsioc",
                    "industry_name_nzsioc",
                )
                .collect()
            )
            return [
                IndustryRecord(
                    industry_code=row.industry_code_nzsioc,
                    industry_name=row.industry_name_nzsioc,
                    aggregation_level=row.industry_aggregation_nzsioc,
                    available_years=tuple(row.available_years),
                )
                for row in rows
            ]
        except AnalyticalStorageError:
            raise
        except Exception as error:
            raise AnalyticalStorageError("Gold industry query failed.") from error

    def get_metrics(
        self, *, industry_code: str, year: int, aggregation_level: str
    ) -> Sequence[MetricRecord]:
        """Return existing M1-M6 Gold observations for one industry/year."""
        try:
            rows = (
                self._load_gold()
                .where(
                    (F.col("industry_code_nzsioc") == industry_code)
                    & (F.col("year") == year)
                    & (
                        F.col("industry_aggregation_nzsioc")
                        == aggregation_level
                    )
                )
                .orderBy("metric_id")
                .collect()
            )
            return [_metric_record(row) for row in rows]
        except AnalyticalStorageError:
            raise
        except Exception as error:
            raise AnalyticalStorageError("Gold performance query failed.") from error

    def get_trend(
        self,
        *,
        industry_code: str,
        metric_id: str,
        aggregation_level: str,
        start_year: int | None,
        end_year: int | None,
    ) -> Sequence[MetricRecord]:
        """Return existing Gold observations in chronological order."""
        try:
            selected = self._load_gold().where(
                (F.col("industry_code_nzsioc") == industry_code)
                & (F.col("metric_id") == metric_id)
                & (F.col("industry_aggregation_nzsioc") == aggregation_level)
            )
            if start_year is not None:
                selected = selected.where(F.col("year") >= start_year)
            if end_year is not None:
                selected = selected.where(F.col("year") <= end_year)
            return [_metric_record(row) for row in selected.orderBy("year").collect()]
        except AnalyticalStorageError:
            raise
        except Exception as error:
            raise AnalyticalStorageError("Gold trend query failed.") from error

    def get_benchmarks(
        self, request: BenchmarkRequest
    ) -> Sequence[BenchmarkRecord]:
        """Delegate ranking entirely to the implemented Phase 8 service."""
        try:
            rows = query_benchmarks(self._spark, self._config, request).collect()
            return [
                BenchmarkRecord(
                    ranking_type=row.ranking_type,
                    rank_position=row.rank_position,
                    year=row.year,
                    aggregation_level=row.industry_aggregation_nzsioc,
                    metric_id=row.metric_id,
                    metric_name=row.metric_name,
                    metric_value=row.metric_value,
                    absolute_metric_value=row.absolute_metric_value,
                    metric_status=row.metric_status,
                    metric_unit=row.metric_unit,
                    industry_code=row.industry_code_nzsioc,
                    industry_name=row.industry_name_nzsioc,
                    metric_record_id=row.metric_record_id,
                    source_silver_record_ids=tuple(row.source_silver_record_ids),
                    source_ingestion_ids=tuple(row.source_ingestion_ids),
                    source_sha256s=tuple(row.source_sha256s),
                    gold_input_fingerprint=row.gold_input_fingerprint,
                    gold_processing_timestamp=row.gold_processing_timestamp,
                )
                for row in rows
            ]
        except (BenchmarkError, OSError, ValueError) as error:
            raise AnalyticalStorageError("Gold benchmark query failed.") from error
        except Exception as error:
            raise AnalyticalStorageError("Gold benchmark query failed.") from error

    def _load_gold(self) -> DataFrame:
        gold_path = self._config.gold_metrics_path.resolve()
        gold_uri = gold_path.as_uri()
        if not DeltaTable.isDeltaTable(self._spark, gold_uri):
            raise AnalyticalStorageError("Gold Delta storage is unavailable.")
        gold = self._spark.read.format("delta").load(gold_uri)
        validate_gold_benchmark_schema(gold)
        return gold


def _metric_record(row: object) -> MetricRecord:
    return MetricRecord(
        metric_record_id=row.metric_record_id,
        year=row.year,
        aggregation_level=row.industry_aggregation_nzsioc,
        industry_code=row.industry_code_nzsioc,
        industry_name=row.industry_name_nzsioc,
        metric_id=row.metric_id,
        metric_name=row.metric_name,
        metric_value=row.metric_value,
        metric_status=row.metric_status,
        metric_unit=row.metric_unit,
        current_input_status=row.current_input_status,
        prior_input_status=row.prior_input_status,
        source_silver_record_ids=tuple(row.source_silver_record_ids),
        source_ingestion_ids=tuple(row.source_ingestion_ids),
        source_sha256s=tuple(row.source_sha256s),
        gold_input_fingerprint=row.gold_input_fingerprint,
    )
