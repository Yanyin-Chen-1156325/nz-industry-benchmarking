"""Spark-free contract tests for the Databricks SQL repository adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from nz_industry_benchmarking.api.databricks_repository import (
    DatabricksSqlAnalyticsRepository,
    DatabricksSqlConfig,
)
from nz_industry_benchmarking.api.errors import AnalyticalStorageError
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest


class FakeCursor:
    def __init__(
        self,
        rows: list[tuple[object, ...]],
        failure: Exception | None = None,
    ) -> None:
        self.rows = rows
        self.failure = failure
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False

    def execute(self, operation: str, parameters: object) -> None:
        self.executions.append((operation, tuple(parameters)))
        if self.failure is not None:
            raise self.failure

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.test_cursor = cursor
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.test_cursor

    def close(self) -> None:
        self.closed = True


class FakeConnectionFactory:
    def __init__(
        self,
        rows: list[tuple[object, ...]] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.rows = [] if rows is None else rows
        self.failure = failure
        self.connections: list[FakeConnection] = []

    def __call__(self, config: DatabricksSqlConfig) -> FakeConnection:
        connection = FakeConnection(FakeCursor(self.rows, self.failure))
        self.connections.append(connection)
        return connection

    @property
    def cursor(self) -> FakeCursor:
        return self.connections[-1].test_cursor


@pytest.fixture
def config() -> DatabricksSqlConfig:
    return DatabricksSqlConfig(
        server_hostname="dbc-example.cloud.databricks.com",
        http_path="/sql/1.0/warehouses/example",
        access_token="test-secret-token",
    )


def _repository(
    config: DatabricksSqlConfig,
    rows: list[tuple[object, ...]] | None = None,
    failure: Exception | None = None,
) -> tuple[DatabricksSqlAnalyticsRepository, FakeConnectionFactory]:
    factory = FakeConnectionFactory(rows, failure)
    return DatabricksSqlAnalyticsRepository(config, factory), factory


def _metric_row(**changes: object) -> tuple[object, ...]:
    values: dict[str, object] = {
        "metric_record_id": "metric-1",
        "year": 2025,
        "aggregation_level": "Level 1",
        "industry_code": "CC",
        "industry_name": "Manufacturing",
        "metric_id": "M1",
        "metric_name": "Total income",
        "metric_value": Decimal("134105.00"),
        "metric_status": "PUBLISHED",
        "metric_unit": "NZD millions",
        "current_input_status": "PUBLISHED",
        "prior_input_status": None,
        "source_silver_record_ids": ["silver-1"],
        "source_ingestion_ids": ["ingestion-1"],
        "source_sha256s": ["A" * 64],
        "gold_input_fingerprint": "gold-fingerprint",
    }
    values.update(changes)
    return tuple(values.values())


def _benchmark_row(
    *, ranking_type: str, rank: int, code: str, value: str
) -> tuple[object, ...]:
    return (
        ranking_type,
        rank,
        2025,
        "Level 1",
        "M4",
        "Total income year-over-year growth",
        Decimal(value),
        abs(Decimal(value)),
        "PUBLISHED",
        "Percent change",
        code,
        f"Industry {code}",
        f"metric-{code}",
        [f"silver-{code}"],
        ["ingestion-1"],
        ["A" * 64],
        f"fingerprint-{code}",
        datetime(2026, 9, 24, 1, 2, 3),
    )


def _normalized(operation: str) -> str:
    return " ".join(operation.split())


def test_repository_exposes_the_analytics_repository_contract(
    config: DatabricksSqlConfig,
) -> None:
    repository, _ = _repository(config)

    for method_name in (
        "list_industries",
        "get_metrics",
        "get_trend",
        "get_benchmarks",
    ):
        assert callable(getattr(repository, method_name))


def test_list_industries_uses_bound_filters_and_groups_available_years(
    config: DatabricksSqlConfig,
) -> None:
    rows = [
        ("CC", "Manufacturing", "Level 1", 2025),
        ("CC", "Manufacturing", "Level 1", 2024),
        ("AA", "Agriculture", "Level 1", 2025),
    ]
    repository, factory = _repository(config, rows)
    unsafe_level = "Level 1' OR 1=1 --"

    records = repository.list_industries(year=2025, aggregation_level=unsafe_level)
    operation, parameters = factory.cursor.executions[0]

    assert "SELECT DISTINCT" in operation
    assert "year = ?" in operation
    assert "industry_aggregation_nzsioc = ?" in operation
    assert unsafe_level not in operation
    assert parameters == (2025, unsafe_level)
    assert records[1].available_years == (2024, 2025)


def test_get_metrics_binds_filters_and_preserves_record_types(
    config: DatabricksSqlConfig,
) -> None:
    rows = [
        _metric_row(
            metric_value=None,
            metric_status="CONFIDENTIAL",
            current_input_status="CONFIDENTIAL",
            source_silver_record_ids=["silver-1", "silver-2"],
        ),
        _metric_row(
            metric_record_id="metric-2",
            metric_id="M2",
            metric_value="123.4500",
        ),
    ]
    repository, factory = _repository(config, rows)
    unsafe_code = "CC' OR 1=1 --"

    records = repository.get_metrics(
        industry_code=unsafe_code, year=2025, aggregation_level="Level 1"
    )
    operation, parameters = factory.cursor.executions[0]

    assert "ORDER BY metric_id" in operation
    assert unsafe_code not in operation
    assert parameters == (unsafe_code, 2025, "Level 1")
    assert records[0].metric_value is None
    assert records[0].metric_status == "CONFIDENTIAL"
    assert records[0].current_input_status == "CONFIDENTIAL"
    assert records[0].prior_input_status is None
    assert records[0].source_silver_record_ids == ("silver-1", "silver-2")
    assert records[1].metric_value == Decimal("123.4500")
    assert isinstance(records[1].metric_value, Decimal)


def test_get_trend_binds_optional_bounds_and_orders_by_year(
    config: DatabricksSqlConfig,
) -> None:
    repository, factory = _repository(
        config,
        [_metric_row(year=2024), _metric_row(year=2025)],
    )

    records = repository.get_trend(
        industry_code="CC",
        metric_id="M4",
        aggregation_level="Level 1",
        start_year=2024,
        end_year=2025,
    )
    operation, parameters = factory.cursor.executions[0]

    assert "year >= ?" in operation
    assert "year <= ?" in operation
    assert "ORDER BY year" in operation
    assert parameters == ("CC", "M4", "Level 1", 2024, 2025)
    assert [record.year for record in records] == [2024, 2025]


@pytest.mark.parametrize(
    ("ranking_type", "value_filter", "primary_order", "values"),
    [
        ("top_increases", "metric_value > 0", "metric_value DESC", ("8", "5")),
        ("top_decreases", "metric_value < 0", "metric_value ASC", ("-8", "-5")),
        (
            "largest_movements",
            None,
            "ABS(metric_value) DESC",
            ("-8", "5"),
        ),
    ],
)
def test_benchmark_sql_matches_phase_8_ranking_semantics(
    config: DatabricksSqlConfig,
    ranking_type: str,
    value_filter: str | None,
    primary_order: str,
    values: tuple[str, str],
) -> None:
    rows = [
        _benchmark_row(ranking_type=ranking_type, rank=1, code="AA", value=values[0]),
        _benchmark_row(ranking_type=ranking_type, rank=2, code="BB", value=values[1]),
    ]
    repository, factory = _repository(config, rows)
    request = BenchmarkRequest(2025, "M4", "Level 1", ranking_type, 2)

    records = repository.get_benchmarks(request)
    operation, parameters = factory.cursor.executions[0]
    sql = _normalized(operation)

    assert "metric_status = ?" in sql
    assert "metric_value IS NOT NULL" in sql
    if value_filter is None:
        assert "metric_value > 0" not in sql
        assert "metric_value < 0" not in sql
    else:
        assert value_filter in sql
    expected_order = (
        f"{primary_order}, industry_code_nzsioc ASC, "
        "industry_name_nzsioc ASC, metric_record_id ASC"
    )
    assert expected_order in sql
    assert "PARTITION BY year, metric_id, industry_aggregation_nzsioc" in sql
    assert "rank_position <= ?" in sql
    assert parameters == (
        2025,
        "M4",
        "Level 1",
        "PUBLISHED",
        ranking_type,
        2,
    )
    assert [record.rank_position for record in records] == [1, 2]
    assert [record.metric_value for record in records] == [
        Decimal(values[0]),
        Decimal(values[1]),
    ]
    assert all(record.metric_status == "PUBLISHED" for record in records)


@pytest.mark.parametrize("field_name", ["catalog", "schema", "gold_table"])
@pytest.mark.parametrize(
    "invalid_identifier",
    ["bad-name", "has space", "1starts_with_digit", "name;DROP_TABLE"],
)
def test_invalid_configured_identifiers_are_rejected(
    field_name: str, invalid_identifier: str
) -> None:
    values = {
        "server_hostname": "dbc-example.cloud.databricks.com",
        "http_path": "/sql/1.0/warehouses/example",
        "access_token": "test-secret-token",
        field_name: invalid_identifier,
    }

    with pytest.raises(ValueError, match=field_name):
        DatabricksSqlConfig(**values)


def test_config_loads_credentials_and_identifiers_from_environment() -> None:
    config = DatabricksSqlConfig.from_environment(
        {
            "DATABRICKS_SERVER_HOSTNAME": "dbc-example.cloud.databricks.com",
            "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/example",
            "DATABRICKS_TOKEN": "test-secret-token",
            "DATABRICKS_CATALOG": "analytics",
            "DATABRICKS_SCHEMA": "reporting",
            "DATABRICKS_GOLD_TABLE": "gold_metrics",
        }
    )

    assert config.qualified_gold_table == ("`analytics`.`reporting`.`gold_metrics`")
    assert "test-secret-token" not in repr(config)


def test_connection_and_cursor_are_closed_after_success(
    config: DatabricksSqlConfig,
) -> None:
    repository, factory = _repository(config, [])

    repository.list_industries(year=None, aggregation_level=None)

    assert factory.cursor.closed is True
    assert factory.connections[0].closed is True


def test_connector_failure_is_sanitized_and_resources_are_closed(
    config: DatabricksSqlConfig,
) -> None:
    connector_message = (
        "authentication failed for token=test-secret-token at "
        "dbc-example.cloud.databricks.com"
    )
    repository, factory = _repository(config, failure=RuntimeError(connector_message))

    with pytest.raises(AnalyticalStorageError) as caught:
        repository.get_metrics(
            industry_code="CC", year=2025, aggregation_level="Level 1"
        )

    assert str(caught.value) == "Databricks Gold performance query failed."
    assert "test-secret-token" not in str(caught.value)
    assert "dbc-example" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert factory.cursor.closed is True
    assert factory.connections[0].closed is True
