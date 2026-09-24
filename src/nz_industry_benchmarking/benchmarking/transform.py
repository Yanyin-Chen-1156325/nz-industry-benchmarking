"""Deterministic ranking transformations over approved Gold change metrics."""

from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from nz_industry_benchmarking.benchmarking.contract import (
    BENCHMARK_OUTPUT_COLUMNS,
    CHANGE_METRIC_IDS,
    GOLD_BENCHMARK_COLUMN_TYPES,
    RANKING_TYPES,
)
from nz_industry_benchmarking.benchmarking.errors import BenchmarkSchemaError

PARTITION_COLUMNS = (
    "year",
    "metric_id",
    "industry_aggregation_nzsioc",
)


def validate_gold_benchmark_schema(gold: DataFrame) -> None:
    """Require the Gold fields and types used by the benchmark query."""
    actual_types = {
        field.name: field.dataType.simpleString() for field in gold.schema.fields
    }
    missing = sorted(set(GOLD_BENCHMARK_COLUMN_TYPES) - set(actual_types))
    mismatches = {
        column: {"expected": expected, "actual": actual_types.get(column)}
        for column, expected in GOLD_BENCHMARK_COLUMN_TYPES.items()
        if column in actual_types and actual_types[column] != expected
    }
    if missing or mismatches:
        raise BenchmarkSchemaError(
            "Gold schema does not satisfy the benchmarking contract. "
            f"Missing={missing!r}; types={mismatches!r}."
        )


def rank_change_metrics(
    gold: DataFrame,
    *,
    ranking_type: str,
    top_n: int,
) -> DataFrame:
    """Rank published M4-M6 rows independently by year, metric, and level."""
    validate_gold_benchmark_schema(gold)
    if ranking_type not in RANKING_TYPES:
        raise ValueError(
            f"ranking_type must be one of {RANKING_TYPES}; got {ranking_type!r}."
        )
    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    eligible = gold.where(
        (F.col("metric_id").isin(*CHANGE_METRIC_IDS))
        & (F.col("metric_status") == "PUBLISHED")
        & F.col("metric_value").isNotNull()
    )
    if ranking_type == "top_increases":
        eligible = eligible.where(F.col("metric_value") > 0)
        primary_order = F.col("metric_value").desc()
    elif ranking_type == "top_decreases":
        eligible = eligible.where(F.col("metric_value") < 0)
        primary_order = F.col("metric_value").asc()
    else:
        primary_order = F.abs(F.col("metric_value")).desc()

    # Stable tie-break after the concept-specific value ordering.
    ordering = (
        primary_order,
        F.col("industry_code_nzsioc").asc(),
        F.col("industry_name_nzsioc").asc(),
        F.col("metric_record_id").asc(),
    )
    window = Window.partitionBy(*PARTITION_COLUMNS).orderBy(*ordering)
    return (
        eligible.withColumn("ranking_type", F.lit(ranking_type))
        .withColumn("absolute_metric_value", F.abs(F.col("metric_value")))
        .withColumn("rank_position", F.row_number().over(window))
        .where(F.col("rank_position") <= top_n)
        .select(*BENCHMARK_OUTPUT_COLUMNS)
    )
