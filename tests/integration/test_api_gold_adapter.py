"""One small HTTP-to-Gold Delta adapter integration test."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from nz_industry_benchmarking.api.app import create_app
from nz_industry_benchmarking.api.repository import SparkGoldRepository
from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.gold.transform import transform_silver_to_gold
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def test_api_adapter_reads_gold_and_reuses_benchmark_service(
    spark, bronze_dataframe_factory, tmp_path
) -> None:
    bronze = bronze_dataframe_factory(
        {"Year": "2024", "Industry_code_NZSIOC": "AA", "Value": "100"},
        {"Year": "2025", "Industry_code_NZSIOC": "AA", "Value": "110"},
        {
            "Year": "2025",
            "Industry_code_NZSIOC": "AA",
            "Variable_code": "H23",
            "Variable_name": "Surplus before income tax",
            "Value": "C",
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
    gold_path = tmp_path / "api-gold"
    gold.write.format("delta").mode("overwrite").save(gold_path.resolve().as_uri())

    repository = SparkGoldRepository(
        spark, BenchmarkConfig(gold_metrics_path=gold_path)
    )
    with TestClient(create_app(repository)) as client:
        industries = client.get(
            "/api/industries",
            params={"year": 2025, "aggregation_level": "Level 1"},
        )
        performance = client.get(
            "/api/industries/AA/performance",
            params={"year": 2025, "aggregation_level": "Level 1"},
        )
        trend = client.get(
            "/api/industries/AA/trend",
            params={"metric_id": "M1", "aggregation_level": "Level 1"},
        )
        benchmark = client.get(
            "/api/benchmarks",
            params={
                "year": 2025,
                "metric_id": "M4",
                "aggregation_level": "Level 1",
                "ranking_type": "top_increases",
                "top_n": 1,
            },
        )

    assert industries.status_code == 200
    assert industries.json()["count"] == 2
    protected = next(
        row for row in performance.json()["metrics"] if row["metric_id"] == "M2"
    )
    assert protected["metric_status"] == "CONFIDENTIAL"
    assert protected["metric_value"] is None
    assert [row["year"] for row in trend.json()["observations"]] == [2024, 2025]
    assert benchmark.status_code == 200
    assert benchmark.json()["results"][0]["industry_code"] == "BB"
    assert benchmark.json()["results"][0]["metric_value"] == 20.0
