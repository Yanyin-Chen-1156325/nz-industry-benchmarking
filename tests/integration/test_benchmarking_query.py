"""Delta integration coverage for the Gold-only benchmark service."""

from __future__ import annotations

from datetime import UTC, datetime

from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest
from nz_industry_benchmarking.benchmarking.service import query_benchmarks
from nz_industry_benchmarking.gold.transform import transform_silver_to_gold
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def test_query_reads_gold_delta_and_returns_a_bounded_ranking(
    spark, bronze_dataframe_factory, tmp_path
) -> None:
    bronze = bronze_dataframe_factory(
        {
            "Year": "2024",
            "Industry_code_NZSIOC": "AA",
            "Value": "100",
        },
        {
            "Year": "2025",
            "Industry_code_NZSIOC": "AA",
            "Value": "110",
        },
        {
            "Year": "2024",
            "Industry_code_NZSIOC": "BB",
            "Industry_name_NZSIOC": "Industry BB",
            "Value": "100",
        },
        {
            "Year": "2025",
            "Industry_code_NZSIOC": "BB",
            "Industry_name_NZSIOC": "Industry BB",
            "Value": "120",
        },
    )
    processed_at = datetime(2026, 9, 24, 1, 2, 3, tzinfo=UTC)
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint="SILVER",
        processing_timestamp=processed_at,
    )
    gold = transform_silver_to_gold(
        silver,
        input_fingerprint="GOLD",
        processing_timestamp=processed_at,
    )
    gold_path = tmp_path / "gold"
    gold.write.format("delta").mode("overwrite").save(gold_path.resolve().as_uri())

    result = query_benchmarks(
        spark,
        BenchmarkConfig(gold_metrics_path=gold_path),
        BenchmarkRequest(
            year=2025,
            metric_id="M4",
            aggregation_level="Level 1",
            ranking_type="top_increases",
            top_n=1,
        ),
    ).collect()

    assert len(result) == 1
    assert result[0].industry_code_nzsioc == "BB"
    assert result[0].rank_position == 1
    assert result[0].metric_value > 0
    assert result[0].source_silver_record_ids
