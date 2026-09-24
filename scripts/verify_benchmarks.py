"""Run and verify representative Phase 8 rankings against actual Gold Delta."""

from __future__ import annotations

import json
from decimal import Decimal

from delta.tables import DeltaTable
from pyspark.sql import functions as F

from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.benchmarking.contract import (
    CHANGE_METRIC_IDS,
    RANKING_TYPES,
)
from nz_industry_benchmarking.benchmarking.transform import rank_change_metrics
from nz_industry_benchmarking.bronze.spark import create_spark_session

YEAR = 2025
AGGREGATION_LEVEL = "Level 1"
TOP_N = 3


def main() -> None:
    """Print actual representative results after enforcing Phase 8 invariants."""
    config = BenchmarkConfig.from_environment()
    spark = create_spark_session(
        master=config.spark_master,
        app_name="nz-industry-benchmarking-verify-rankings",
    )
    spark.sparkContext.setLogLevel(config.spark_log_level)
    try:
        gold_uri = config.gold_metrics_path.resolve().as_uri()
        if not DeltaTable.isDeltaTable(spark, gold_uri):
            raise RuntimeError(f"Gold Delta table is unavailable: {gold_uri}")
        gold = spark.read.format("delta").load(gold_uri).cache()
        cases: list[dict[str, object]] = []
        all_ranked = []
        for ranking_type in RANKING_TYPES:
            ranked = rank_change_metrics(
                gold,
                ranking_type=ranking_type,
                top_n=TOP_N,
            ).cache()
            all_ranked.append(ranked)
            for metric_id in CHANGE_METRIC_IDS:
                rows = (
                    ranked.where(
                        (F.col("year") == YEAR)
                        & (F.col("metric_id") == metric_id)
                        & (
                            F.col("industry_aggregation_nzsioc")
                            == AGGREGATION_LEVEL
                        )
                    )
                    .orderBy("rank_position")
                    .collect()
                )
                _verify_case(rows, ranking_type, metric_id)
                cases.append(
                    {
                        "year": YEAR,
                        "aggregation_level": AGGREGATION_LEVEL,
                        "metric_id": metric_id,
                        "ranking_type": ranking_type,
                        "results": [
                            {
                                "rank": row.rank_position,
                                "industry_code": row.industry_code_nzsioc,
                                "industry_name": row.industry_name_nzsioc,
                                "signed_value": row.metric_value,
                                "absolute_value": row.absolute_metric_value,
                                "unit": row.metric_unit,
                                "metric_record_id": row.metric_record_id,
                            }
                            for row in rows
                        ],
                    }
                )

        ranked_ids = all_ranked[0].select("metric_record_id")
        for ranked in all_ranked[1:]:
            ranked_ids = ranked_ids.unionByName(ranked.select("metric_record_id"))
        non_published = (
            ranked_ids.distinct()
            .join(
                gold.select("metric_record_id", "metric_status"),
                "metric_record_id",
            )
            .where(F.col("metric_status") != "PUBLISHED")
            .count()
        )
        if non_published:
            raise AssertionError("A non-PUBLISHED Gold metric entered a ranking.")

        print(
            json.dumps(
                {
                    "gold_path": str(config.gold_metrics_path),
                    "gold_rows": gold.count(),
                    "representative_year": YEAR,
                    "representative_aggregation_level": AGGREGATION_LEVEL,
                    "top_n": TOP_N,
                    "non_published_ranked_rows": non_published,
                    "tie_break": (
                        "industry_code_nzsioc ASC, industry_name_nzsioc ASC, "
                        "metric_record_id ASC"
                    ),
                    "cases": cases,
                },
                indent=2,
                default=_json_default,
            )
        )
    finally:
        spark.stop()


def _verify_case(rows, ranking_type: str, metric_id: str) -> None:
    for expected_rank, row in enumerate(rows, start=1):
        assert row.rank_position == expected_rank
        assert row.year == YEAR
        assert row.metric_id == metric_id
        assert row.industry_aggregation_nzsioc == AGGREGATION_LEVEL
        assert row.metric_unit
        assert row.metric_value is not None
        assert abs(row.metric_value) == row.absolute_metric_value
        if ranking_type == "top_increases":
            assert row.metric_value > 0
        elif ranking_type == "top_decreases":
            assert row.metric_value < 0


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


if __name__ == "__main__":
    main()
