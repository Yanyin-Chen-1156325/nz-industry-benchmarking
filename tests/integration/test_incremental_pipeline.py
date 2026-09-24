"""End-to-end proof of safe Phase 9 decisions over Delta layers."""

from __future__ import annotations

import csv
from pathlib import Path

from delta.tables import DeltaTable

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.service import run_incremental_pipeline
from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS
from nz_industry_benchmarking.silver.config import SilverConfig


def test_incremental_no_op_additive_artifact_and_revision_deferral(
    spark,
    tmp_path: Path,
) -> None:
    source = tmp_path / "aes.csv"
    manifest = tmp_path / "manifest.json"
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"

    _write_year(source, 2024, income="100", surplus="10", return_on_assets="5")
    first_config = _config(
        source,
        manifest,
        bronze_path,
        silver_path,
        gold_path,
        year=2024,
        version="2024-final",
    )
    first = run_incremental_pipeline(spark, first_config)
    bronze_version = _delta_version(spark, bronze_path)
    silver_version = _delta_version(spark, silver_path)
    gold_version = _delta_version(spark, gold_path)

    repeated = run_incremental_pipeline(spark, first_config)

    assert first.initial_plan.pipeline_status == "PROCESS_REQUIRED"
    assert first.final_plan.pipeline_status == "NO_OP"
    assert repeated.initial_plan.pipeline_status == "NO_OP"
    assert repeated.bronze_result is None
    assert repeated.silver_result is None
    assert repeated.gold_result is None
    assert _delta_version(spark, bronze_path) == bronze_version
    assert _delta_version(spark, silver_path) == silver_version
    assert _delta_version(spark, gold_path) == gold_version
    assert spark.read.format("delta").load(bronze_path.as_uri()).count() == 3

    _write_year(source, 2025, income="120", surplus="8", return_on_assets="4")
    new_config = _config(
        source,
        manifest,
        bronze_path,
        silver_path,
        gold_path,
        year=2025,
        version="2025-provisional",
    )
    additive = run_incremental_pipeline(spark, new_config)

    assert additive.initial_plan.artifact_status == "NEW_ARTIFACT"
    assert additive.initial_plan.overlap_observations == 0
    assert additive.bronze_result is not None
    assert additive.silver_result is not None
    assert additive.gold_result is not None
    assert additive.final_plan.pipeline_status == "NO_OP"
    assert spark.read.format("delta").load(bronze_path.as_uri()).count() == 6

    _write_year(source, 2024, income="101", surplus="10", return_on_assets="5")
    revised_config = _config(
        source,
        manifest,
        bronze_path,
        silver_path,
        gold_path,
        year=2024,
        version="2024-revised-candidate",
    )
    deferred = run_incremental_pipeline(spark, revised_config)

    assert deferred.initial_plan.pipeline_status == "DEFERRED_REVISION"
    assert deferred.initial_plan.overlap_observations == 3
    assert deferred.initial_plan.changed_existing_observations == 1
    assert deferred.initial_plan.revision_sensitive is True
    assert deferred.bronze_result is None
    assert deferred.silver_result is None
    assert deferred.gold_result is None
    assert spark.read.format("delta").load(bronze_path.as_uri()).count() == 6


def _config(
    source: Path,
    manifest: Path,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
    *,
    year: int,
    version: str,
) -> IncrementalConfig:
    return IncrementalConfig(
        ingestion=IngestionConfig(
            source_file=source,
            source_url="https://www.stats.govt.nz/aes.csv",
            dataset_year=year,
            dataset_version=version,
            schema_version="aes-public-csv-v1",
            manifest_file=manifest,
        ),
        bronze=BronzeConfig(table_path=bronze_path),
        silver=SilverConfig(bronze_path=bronze_path, silver_path=silver_path),
        gold=GoldConfig(silver_path=silver_path, gold_metrics_path=gold_path),
    )


def _write_year(
    path: Path,
    year: int,
    *,
    income: str,
    surplus: str,
    return_on_assets: str,
) -> None:
    rows = [
        _row(year, "H01", "Total income", "Financial performance", income),
        _row(
            year,
            "H23",
            "Surplus before income tax",
            "Financial performance",
            surplus,
        ),
        _row(
            year,
            "H40",
            "Return on total assets",
            "Financial ratios",
            return_on_assets,
            units="Percentage",
        ),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(
    year: int,
    code: str,
    name: str,
    category: str,
    value: str,
    *,
    units: str = "Dollars (millions)",
) -> dict[str, str]:
    return {
        "Year": str(year),
        "Industry_aggregation_NZSIOC": "Level 1",
        "Industry_code_NZSIOC": "AA",
        "Industry_name_NZSIOC": "Agriculture, Forestry and Fishing",
        "Units": units,
        "Variable_code": code,
        "Variable_name": name,
        "Variable_category": category,
        "Value": value,
        "Industry_code_ANZSIC06": "ANZSIC06 division A",
    }


def _delta_version(spark, path: Path) -> int:
    return int(DeltaTable.forPath(spark, path.as_uri()).history(1).first().version)
