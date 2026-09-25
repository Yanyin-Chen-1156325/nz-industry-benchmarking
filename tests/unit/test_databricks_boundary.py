"""Spark-free checks for Databricks configuration and session ownership."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

import nz_industry_benchmarking.databricks.pipeline as pipeline
from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.databricks.config import DatabricksInitialLoadConfig
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.quality.models import QualityReport
from nz_industry_benchmarking.silver.models import SilverWriteResult


def test_databricks_config_builds_expected_catalog_targets() -> None:
    config = DatabricksInitialLoadConfig(Path("/Volumes/workspace/demo/aes.csv"))

    assert config.bronze_target.identifier == (
        "workspace.nz_industry_benchmarking.bronze_aes"
    )
    assert config.silver_target.identifier == (
        "workspace.nz_industry_benchmarking.silver_aes_observations"
    )
    assert config.gold_target.identifier == (
        "workspace.nz_industry_benchmarking.gold_industry_financial_metrics"
    )
    assert config.ingestion.source_file == config.source_file


@pytest.mark.parametrize(
    "changes",
    [
        {"catalog": "bad-name"},
        {"schema": ""},
        {"gold_table": "three.parts"},
        {"dataset_year": 1999},
        {"dataset_version": ""},
        {"source_url": ""},
        {"source_file": Path()},
        {"silver_table": "bronze_aes"},
    ],
)
def test_databricks_config_rejects_invalid_values(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "source_file": Path("/Volumes/workspace/demo/aes.csv"),
        **changes,
    }
    with pytest.raises((TypeError, ValueError)):
        DatabricksInitialLoadConfig(**values)


def test_databricks_entrypoint_uses_only_supplied_spark(
    monkeypatch: pytest.MonkeyPatch,
    bronze_outcome,
) -> None:
    supplied_spark = object()
    frames = {"bronze": object(), "silver": object(), "gold": object()}
    storages: dict[str, _FakeStorage] = {}
    observed: dict[str, object] = {}
    timestamp = datetime(2026, 9, 25, tzinfo=UTC)

    def storage_factory(spark, target):
        assert spark is supplied_spark
        storage = _FakeStorage(target.table, frames)
        storages[target.table] = storage
        return storage

    monkeypatch.setattr(pipeline, "CatalogDeltaStorage", storage_factory)
    monkeypatch.setattr(
        pipeline, "prepare_ingestion", lambda config, clock: bronze_outcome
    )

    def build_bronze(spark, outcome):
        observed["spark"] = spark
        assert outcome is bronze_outcome
        return frames["bronze"]

    monkeypatch.setattr(pipeline, "build_bronze_dataframe", build_bronze)
    monkeypatch.setattr(pipeline, "write_bronze_to_storage", _bronze_result)
    monkeypatch.setattr(pipeline, "calculate_input_fingerprint", lambda frame: "SILVER")
    monkeypatch.setattr(
        pipeline, "select_current_bronze_view", lambda frame: _CountFrame(2)
    )
    monkeypatch.setattr(
        pipeline,
        "transform_bronze_to_silver",
        lambda *args, **kwargs: frames["silver"],
    )
    monkeypatch.setattr(pipeline, "write_silver_to_storage", _silver_result)
    monkeypatch.setattr(
        pipeline,
        "assess_silver_quality",
        lambda *args, **kwargs: _quality_result(),
    )
    monkeypatch.setattr(
        pipeline, "calculate_gold_input_fingerprint", lambda frame: "GOLD"
    )
    monkeypatch.setattr(
        pipeline,
        "transform_silver_to_gold",
        lambda *args, **kwargs: _CountFrame(12),
    )
    monkeypatch.setattr(pipeline, "write_gold_to_storage", _gold_result)

    result = pipeline.run_initial_load(
        supplied_spark,
        DatabricksInitialLoadConfig(Path("/Volumes/workspace/demo/aes.csv")),
        clock=lambda: timestamp,
    )

    assert observed["spark"] is supplied_spark
    assert result.bronze.total_rows == 2
    assert result.silver.silver_output_rows == 2
    assert result.quality.overall_result == "PASS"
    assert result.gold.gold_output_rows == 12
    assert set(storages) == {
        "bronze_aes",
        "silver_aes_observations",
        "gold_industry_financial_metrics",
    }


class _FakeStorage:
    def __init__(self, table: str, frames: dict[str, object]) -> None:
        self.table = table
        self.identifier = f"workspace.nz_industry_benchmarking.{table}"
        self._frames = frames

    def exists(self) -> bool:
        return False

    def read(self):
        if self.table.startswith("bronze"):
            return self._frames["bronze"]
        if self.table.startswith("silver"):
            return self._frames["silver"]
        return self._frames["gold"]


class _CountFrame:
    def __init__(self, rows: int) -> None:
        self._rows = rows

    def count(self) -> int:
        return self._rows


def _bronze_result(dataframe, storage, **kwargs) -> BronzeWriteResult:
    return BronzeWriteResult(storage.identifier, "ABC", "ABC", 2, 2, 2, False)


def _silver_result(dataframe, storage, **kwargs) -> SilverWriteResult:
    return SilverWriteResult(
        storage.identifier, "SILVER", 2, 2, 2, 0, {"PUBLISHED": 2}, False
    )


def _quality_result() -> QualityReport:
    return QualityReport(
        dataset_path="workspace.nz_industry_benchmarking.silver_aes_observations",
        generated_at="2026-09-25T00:00:00Z",
        overall_result="PASS",
        rows_processed=2,
        rows_accepted=2,
        rows_rejected=0,
        checks_executed=16,
        passed_checks=16,
        failed_checks=0,
        validation_failure_counts={},
        checks=(),
    )


def _gold_result(dataframe, storage, **kwargs) -> GoldWriteResult:
    return GoldWriteResult(
        storage.identifier, "GOLD", 2, 12, {"M1": 2}, {"PUBLISHED": 12}, False
    )
