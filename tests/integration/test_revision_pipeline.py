"""End-to-end revision history, current-view, and Gold refresh proof."""

from __future__ import annotations

import csv
from pathlib import Path

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.service import run_incremental_pipeline
from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS
from nz_industry_benchmarking.revision.config import RevisionConfig
from nz_industry_benchmarking.revision.service import run_revision_pipeline
from nz_industry_benchmarking.silver.config import SilverConfig


def test_newer_release_preserves_history_and_refreshes_current_views(
    spark,
    tmp_path: Path,
) -> None:
    source = tmp_path / "aes.csv"
    manifest = tmp_path / "manifest.json"
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"
    reports = tmp_path / "revisions"

    _write_release(source, income="100", surplus="10", assets="5")
    old_pipeline = _pipeline_config(
        source,
        manifest,
        bronze_path,
        silver_path,
        gold_path,
        dataset_year=2025,
        version="2025-provisional",
    )
    first = run_incremental_pipeline(spark, old_pipeline)
    old_gold_fingerprint = first.gold_result.input_fingerprint

    _write_release(source, income="110", surplus="C", assets="S")
    new_pipeline = _pipeline_config(
        source,
        manifest,
        bronze_path,
        silver_path,
        gold_path,
        dataset_year=2026,
        version="2026-provisional",
    )
    deferred = run_incremental_pipeline(spark, new_pipeline)
    assert deferred.initial_plan.pipeline_status == "DEFERRED_REVISION"

    config = RevisionConfig(pipeline=new_pipeline, report_dir=reports)
    applied = run_revision_pipeline(spark, config)
    bronze = spark.read.format("delta").load(bronze_path.as_uri())
    silver = spark.read.format("delta").load(silver_path.as_uri())
    gold = spark.read.format("delta").load(gold_path.as_uri())

    assert applied.report.overall_result == "APPLIED"
    assert applied.report.overlapping_observations == 4
    assert applied.report.unchanged_republications == 1
    assert applied.report.revised_values == 3
    assert applied.report.value_transition_counts == {
        "PUBLISHED->CONFIDENTIAL": 1,
        "PUBLISHED->PUBLISHED": 1,
        "PUBLISHED->SUPPRESSED": 1,
    }
    assert len(applied.report.previous_releases) == 1
    assert applied.report.incoming_release["dataset_year"] == 2026
    incoming_sha256 = str(applied.report.incoming_release["source_sha256"])
    previous_sha256 = str(applied.report.previous_releases[0]["source_sha256"])
    assert incoming_sha256 != previous_sha256
    assert bronze.count() == 8
    assert bronze.select("ingestion_id").distinct().count() == 2
    assert silver.count() == 4
    assert silver.select(
        "year",
        "industry_aggregation_nzsioc",
        "industry_code_nzsioc",
        "variable_code",
    ).distinct().count() == 4
    assert silver.select("dataset_year").distinct().first()[0] == 2026
    assert silver.select("source_sha256").distinct().first()[0] == incoming_sha256
    assert silver.where("variable_code = 'H23'").first().value_status == "CONFIDENTIAL"
    assert silver.where("variable_code = 'H40'").first().value_status == "SUPPRESSED"
    assert applied.gold_result.input_fingerprint != old_gold_fingerprint
    assert gold.where("metric_id = 'M1'").first().metric_value == 110
    assert gold.where("metric_id = 'M2'").first().metric_status == "CONFIDENTIAL"
    assert gold.where("metric_id = 'M3'").first().metric_status == "SUPPRESSED"
    assert gold.where("metric_id = 'M1'").first().source_sha256s == [incoming_sha256]

    repeated = run_revision_pipeline(spark, config)
    assert repeated.duplicate is True
    assert repeated.report == applied.report
    assert repeated.bronze_result is None
    assert spark.read.format("delta").load(bronze_path.as_uri()).count() == 8
    assert len(list(reports.glob("*.json"))) == 1


def _pipeline_config(
    source: Path,
    manifest: Path,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
    *,
    dataset_year: int,
    version: str,
) -> IncrementalConfig:
    return IncrementalConfig(
        ingestion=IngestionConfig(
            source_file=source,
            source_url="https://www.stats.govt.nz/aes.csv",
            dataset_year=dataset_year,
            dataset_version=version,
            schema_version="aes-public-csv-v1",
            manifest_file=manifest,
        ),
        bronze=BronzeConfig(table_path=bronze_path),
        silver=SilverConfig(bronze_path=bronze_path, silver_path=silver_path),
        gold=GoldConfig(silver_path=silver_path, gold_metrics_path=gold_path),
    )


def _write_release(
    path: Path,
    *,
    income: str,
    surplus: str,
    assets: str,
) -> None:
    rows = [
        _row("H01", "Total income", "Financial performance", income),
        _row(
            "H23",
            "Surplus before income tax",
            "Financial performance",
            surplus,
        ),
        _row(
            "H40",
            "Return on total assets",
            "Financial ratios",
            assets,
            units="Percentage",
        ),
        _row("H08", "Total expenditure", "Financial performance", "50"),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(
    code: str,
    name: str,
    category: str,
    value: str,
    *,
    units: str = "Dollars (millions)",
) -> dict[str, str]:
    return {
        "Year": "2024",
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
