"""Spark-free configuration and repository-selection tests."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from nz_industry_benchmarking.api.app import create_app
from nz_industry_benchmarking.api.config import AnalyticsBackend, ApiConfig
from nz_industry_benchmarking.api.databricks_repository import (
    DatabricksSqlAnalyticsRepository,
)
from nz_industry_benchmarking.api.repository_provider import configured_repository


def _databricks_environment(**overrides: str) -> dict[str, str]:
    environment = {
        "NZIB_ANALYTICS_BACKEND": "databricks-sql",
        "DATABRICKS_SERVER_HOSTNAME": "dbc-example.cloud.databricks.com",
        "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/example",
        "DATABRICKS_TOKEN": "test-secret-token",
    }
    environment.update(overrides)
    return environment


class FakeSparkContext:
    def __init__(self) -> None:
        self.log_level: str | None = None

    def setLogLevel(self, level: str) -> None:
        self.log_level = level


class FakeSparkSession:
    def __init__(self) -> None:
        self.sparkContext = FakeSparkContext()
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def test_default_backend_is_local_spark() -> None:
    config = ApiConfig.from_environment({})

    assert config.analytics_backend is AnalyticsBackend.LOCAL_SPARK
    assert config.databricks_sql is None


def test_explicit_local_spark_selects_spark_repository() -> None:
    from nz_industry_benchmarking.api.repository import SparkGoldRepository

    config = ApiConfig.from_environment({"NZIB_ANALYTICS_BACKEND": "local-spark"})
    spark = FakeSparkSession()

    with configured_repository(
        config, spark_session_factory=lambda **kwargs: spark
    ) as repository:
        assert isinstance(repository, SparkGoldRepository)
        assert spark.sparkContext.log_level == config.benchmark.spark_log_level
        assert spark.stopped is False

    assert spark.stopped is True


def test_databricks_sql_selects_databricks_repository_without_connection() -> None:
    config = ApiConfig.from_environment(_databricks_environment())

    with configured_repository(config) as repository:
        assert isinstance(repository, DatabricksSqlAnalyticsRepository)


def test_unknown_backend_fails_clearly() -> None:
    with pytest.raises(ValueError, match="local-spark.*databricks-sql"):
        ApiConfig.from_environment({"NZIB_ANALYTICS_BACKEND": "automatic"})


@pytest.mark.parametrize(
    ("missing_name", "environment_name"),
    [
        ("hostname", "DATABRICKS_SERVER_HOSTNAME"),
        ("HTTP path", "DATABRICKS_HTTP_PATH"),
        ("token", "DATABRICKS_TOKEN"),
    ],
)
def test_missing_databricks_connection_config_fails_safely(
    missing_name: str, environment_name: str
) -> None:
    environment = _databricks_environment()
    del environment[environment_name]

    with pytest.raises(ValueError) as caught:
        ApiConfig.from_environment(environment)

    message = str(caught.value)
    assert environment_name in message
    assert missing_name.lower() not in message.lower() or environment_name in message
    assert "test-secret-token" not in message
    assert "dbc-example.cloud.databricks.com" not in message


def test_databricks_sql_selection_does_not_call_spark_factory() -> None:
    config = ApiConfig.from_environment(_databricks_environment())

    def fail_if_called(**kwargs: object) -> FakeSparkSession:
        raise AssertionError(f"Spark must not be created: {kwargs}")

    with configured_repository(
        config, spark_session_factory=fail_if_called
    ) as repository:
        assert isinstance(repository, DatabricksSqlAnalyticsRepository)


def test_fastapi_uses_selected_databricks_repository_and_contracts_remain_valid() -> (
    None
):
    config = ApiConfig.from_environment(_databricks_environment())
    application = create_app(config=config)

    with TestClient(application) as client:
        response = client.get("/api/health")
        selected = application.state.analytics_repository

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert isinstance(selected, DatabricksSqlAnalyticsRepository)


def test_databricks_fastapi_startup_does_not_import_spark_or_delta() -> None:
    script = r"""
import builtins

original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "pyspark" or name.startswith("pyspark."):
        raise AssertionError(f"unexpected Spark import: {name}")
    if name == "delta" or name.startswith("delta."):
        raise AssertionError(f"unexpected Delta import: {name}")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import

from fastapi.testclient import TestClient
from nz_industry_benchmarking.api.app import app

with TestClient(app) as client:
    assert client.get("/api/health").json() == {"status": "ok"}
"""
    environment = {
        **os.environ,
        **_databricks_environment(),
        "PYTHONPATH": "src",
    }

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
