"""Read-only orchestration for benchmark queries over Gold Delta."""

from __future__ import annotations

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession

from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.benchmarking.errors import BenchmarkSourceError
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest
from nz_industry_benchmarking.benchmarking.transform import rank_change_metrics


def query_benchmarks(
    spark: SparkSession,
    config: BenchmarkConfig,
    request: BenchmarkRequest,
) -> DataFrame:
    """Read Gold Delta only and return one requested benchmark result."""
    gold_path = config.gold_metrics_path.resolve()
    gold_uri = gold_path.as_uri()
    if not DeltaTable.isDeltaTable(spark, gold_uri):
        raise BenchmarkSourceError(
            f"Gold Delta table does not exist or is invalid: {gold_path}"
        )

    gold = spark.read.format("delta").load(gold_uri)
    selected = gold.where(
        (gold.year == request.year)
        & (gold.metric_id == request.metric_id)
        & (gold.industry_aggregation_nzsioc == request.aggregation_level)
    )
    return rank_change_metrics(
        selected,
        ranking_type=request.ranking_type,
        top_n=request.top_n,
    ).orderBy("rank_position")
