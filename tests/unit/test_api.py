"""Spark-free HTTP contract tests for the Phase 12 API."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from nz_industry_benchmarking.api.app import create_app
from nz_industry_benchmarking.api.config import ApiConfig
from nz_industry_benchmarking.api.errors import AnalyticalStorageError
from nz_industry_benchmarking.api.records import (
    BenchmarkRecord,
    IndustryRecord,
    MetricRecord,
)


def _metric(**overrides: object) -> MetricRecord:
    base = MetricRecord(
        metric_record_id="metric-1",
        year=2025,
        aggregation_level="Level 1",
        industry_code="CC",
        industry_name="Manufacturing",
        metric_id="M1",
        metric_name="Total income",
        metric_value=Decimal("134105"),
        metric_status="PUBLISHED",
        metric_unit="NZD millions",
        current_input_status="PUBLISHED",
        prior_input_status=None,
        source_silver_record_ids=("silver-1",),
        source_ingestion_ids=("ingestion-1",),
        source_sha256s=("A" * 64,),
        gold_input_fingerprint="gold-fingerprint",
    )
    return replace(base, **overrides)


class FakeRepository:
    """Small deterministic repository used to isolate the HTTP layer."""

    def __init__(self) -> None:
        self.empty = False
        self.failure: Exception | None = None
        self.benchmark_request = None

    def _check(self) -> None:
        if self.failure is not None:
            raise self.failure

    def list_industries(self, *, year, aggregation_level):
        self._check()
        if self.empty:
            return []
        return [
            IndustryRecord("CC", "Manufacturing", "Level 1", (2024, 2025))
        ]

    def get_metrics(self, *, industry_code, year, aggregation_level):
        self._check()
        if self.empty:
            return []
        return [
            _metric(),
            _metric(
                metric_record_id="metric-2",
                metric_id="M2",
                metric_name="Surplus before income tax",
                metric_value=Decimal("999"),
                metric_status="CONFIDENTIAL",
                current_input_status="CONFIDENTIAL",
            ),
        ]

    def get_trend(
        self,
        *,
        industry_code,
        metric_id,
        aggregation_level,
        start_year,
        end_year,
    ):
        self._check()
        if self.empty:
            return []
        return [
            _metric(year=2024, metric_value=Decimal("127567")),
            _metric(year=2025, metric_value=Decimal("134105")),
        ]

    def get_benchmarks(self, request):
        self._check()
        self.benchmark_request = request
        if self.empty:
            return []
        return [
            BenchmarkRecord(
                ranking_type=request.ranking_type,
                rank_position=1,
                year=request.year,
                aggregation_level=request.aggregation_level,
                metric_id=request.metric_id,
                metric_name="Total income year-over-year growth",
                metric_value=Decimal("5.125"),
                absolute_metric_value=Decimal("5.125"),
                metric_status="PUBLISHED",
                metric_unit="Percent change",
                industry_code="CC",
                industry_name="Manufacturing",
                metric_record_id="metric-4",
                source_silver_record_ids=("silver-1", "silver-2"),
                source_ingestion_ids=("ingestion-1",),
                source_sha256s=("A" * 64,),
                gold_input_fingerprint="gold-fingerprint",
                gold_processing_timestamp=datetime(2026, 9, 24, 1, 2, 3),
            )
        ]


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def client(repository: FakeRepository):
    with TestClient(create_app(repository)) as test_client:
        yield test_client


def test_health_and_openapi_are_available_without_storage_query(
    client: TestClient,
) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    schema = client.get("/openapi.json").json()
    assert "/api/benchmarks" in schema["paths"]
    assert "/api/industries/{industry}/trend" in schema["paths"]


def test_frontend_origin_is_allowed_without_wildcard_cors(
    client: TestClient,
) -> None:
    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:8080"})
    blocked = client.get(
        "/api/health", headers={"Origin": "https://untrusted.example"}
    )

    assert response.headers["access-control-allow-origin"] == ("http://127.0.0.1:8080")
    assert "access-control-allow-origin" not in blocked.headers


def test_api_cors_origins_are_configurable() -> None:
    config = ApiConfig.from_environment(
        {"API_CORS_ORIGINS": "https://one.example, https://two.example"}
    )
    assert config.cors_origins == (
        "https://one.example",
        "https://two.example",
    )


def test_lists_available_industries(client: TestClient) -> None:
    response = client.get(
        "/api/industries", params={"year": 2025, "aggregation_level": "Level 1"}
    )
    assert response.status_code == 200
    assert response.json()["industries"][0] == {
        "industry_code": "CC",
        "industry_name": "Manufacturing",
        "aggregation_level": "Level 1",
        "available_years": [2024, 2025],
    }


def test_performance_keeps_protected_status_and_serializes_value_as_null(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/industries/CC/performance",
        params={"year": 2025, "aggregation_level": "Level 1"},
    )
    assert response.status_code == 200
    confidential = response.json()["metrics"][1]
    assert confidential["metric_status"] == "CONFIDENTIAL"
    assert confidential["metric_value"] is None
    assert confidential["current_input_status"] == "CONFIDENTIAL"


def test_trend_preserves_chronological_gold_observations(client: TestClient) -> None:
    response = client.get(
        "/api/industries/CC/trend",
        params={"metric_id": "M1", "aggregation_level": "Level 1"},
    )
    assert response.status_code == 200
    assert [row["year"] for row in response.json()["observations"]] == [2024, 2025]


def test_benchmark_delegates_validated_phase_8_request(
    client: TestClient, repository: FakeRepository
) -> None:
    response = client.get(
        "/api/benchmarks",
        params={
            "year": 2025,
            "metric_id": "M4",
            "aggregation_level": "Level 1",
            "ranking_type": "top_increases",
            "top_n": 5,
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["metric_value"] == 5.125
    assert result["metric_status"] == "PUBLISHED"
    assert result["metric_unit"] == "Percent change"
    assert repository.benchmark_request.top_n == 5


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("metric_id", "M1"),
        ("aggregation_level", "Level 2"),
        ("ranking_type", "best"),
        ("top_n", "0"),
    ],
)
def test_invalid_benchmark_parameters_use_consistent_422_body(
    client: TestClient, parameter: str, value: str
) -> None:
    parameters = {
        "year": "2025",
        "metric_id": "M4",
        "aggregation_level": "Level 1",
        "ranking_type": "largest_movements",
        "top_n": "10",
    }
    parameters[parameter] = value
    response = client.get("/api/benchmarks", params=parameters)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert response.json()["error"]["details"]


def test_no_matching_data_uses_404(
    client: TestClient, repository: FakeRepository
) -> None:
    repository.empty = True
    response = client.get(
        "/api/industries/ZZ/performance",
        params={"year": 2025, "aggregation_level": "Level 1"},
    )
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NO_MATCHING_DATA",
            "message": "No performance data matched the query.",
            "details": [],
        }
    }


def test_storage_failure_is_safe_and_does_not_leak_details(
    repository: FakeRepository,
) -> None:
    repository.failure = AnalyticalStorageError(
        "java.io.FileNotFoundException: C:/secret/local/gold/_delta_log"
    )
    with TestClient(create_app(repository), raise_server_exceptions=False) as client:
        response = client.get("/api/industries")
    assert response.status_code == 503
    body = response.text
    assert response.json()["error"]["code"] == "ANALYTICAL_STORAGE_UNAVAILABLE"
    assert "secret" not in body
    assert "delta_log" not in body


def test_unexpected_failure_is_safe(repository: FakeRepository) -> None:
    repository.failure = RuntimeError("internal stack detail")
    with TestClient(create_app(repository), raise_server_exceptions=False) as client:
        response = client.get("/api/industries")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "stack detail" not in response.text
