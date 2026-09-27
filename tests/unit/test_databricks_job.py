"""Spark-free tests for the Databricks Python wheel-task wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import nz_industry_benchmarking
import nz_industry_benchmarking.databricks.job as job

SOURCE = (
    "/Volumes/workspace/nz_industry_benchmarking/source_files/"
    "annual-enterprise-survey-2025-financial-year-provisional.csv"
)


def test_package_root_exposes_callable_databricks_job() -> None:
    assert callable(nz_industry_benchmarking.databricks_job)


def test_package_root_databricks_job_delegates_to_existing_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def main() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(job, "main", main)

    nz_industry_benchmarking.databricks_job()

    assert calls == 1


def test_argument_defaults_match_initial_load_config() -> None:
    args = job.parse_arguments(["--source-file", SOURCE])

    assert args.source_file == Path(SOURCE)
    assert args.catalog == "workspace"
    assert args.schema == "nz_industry_benchmarking"
    assert args.bronze_table == "bronze_aes"
    assert args.silver_table == "silver_aes_observations"
    assert args.gold_table == "gold_industry_financial_metrics"


def test_explicit_arguments_override_every_default() -> None:
    args = job.parse_arguments(
        [
            "--source-file",
            "/Volumes/custom/source.csv",
            "--catalog",
            "custom_catalog",
            "--schema",
            "custom_schema",
            "--bronze-table",
            "raw_aes",
            "--silver-table",
            "clean_aes",
            "--gold-table",
            "metrics_aes",
        ]
    )

    assert args.source_file == Path("/Volumes/custom/source.csv")
    assert args.catalog == "custom_catalog"
    assert args.schema == "custom_schema"
    assert args.bronze_table == "raw_aes"
    assert args.silver_table == "clean_aes"
    assert args.gold_table == "metrics_aes"


def test_main_constructs_config_and_delegates_to_initial_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supplied_spark = object()
    observed: dict[str, object] = {}
    result = _FakeResult({"status": "complete"})

    monkeypatch.setattr(
        job, "require_active_spark_session", lambda: supplied_spark
    )

    def run_initial_load(spark, config):
        observed["spark"] = spark
        observed["config"] = config
        return result

    monkeypatch.setattr(job, "run_initial_load", run_initial_load)

    job.main(
        [
            "--source-file",
            SOURCE,
            "--catalog",
            "demo_catalog",
            "--schema",
            "demo_schema",
            "--bronze-table",
            "demo_bronze",
            "--silver-table",
            "demo_silver",
            "--gold-table",
            "demo_gold",
        ]
    )

    config = observed["config"]
    assert observed["spark"] is supplied_spark
    assert config.source_file == Path(SOURCE)
    assert config.catalog == "demo_catalog"
    assert config.schema == "demo_schema"
    assert config.bronze_table == "demo_bronze"
    assert config.silver_table == "demo_silver"
    assert config.gold_table == "demo_gold"
    assert result.to_dict_calls == 1


def test_main_prints_readable_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {"quality": {"overall_result": "PASS"}, "rows": 42}
    monkeypatch.setattr(job, "require_active_spark_session", object)
    monkeypatch.setattr(
        job, "run_initial_load", lambda spark, config: _FakeResult(payload)
    )

    job.main(["--source-file", SOURCE])

    output = capsys.readouterr().out
    assert output.startswith("{\n")
    assert json.loads(output) == payload


def test_active_spark_session_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(job.SparkSession, "getActiveSession", lambda: None)

    with pytest.raises(RuntimeError, match="No active SparkSession"):
        job.require_active_spark_session()


class _FakeResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.to_dict_calls = 0

    def to_dict(self) -> dict[str, object]:
        self.to_dict_calls += 1
        return self.payload
