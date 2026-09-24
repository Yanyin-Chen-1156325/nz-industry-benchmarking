"""Checks for the Phase 2 project foundation."""

import sys

import nz_industry_benchmarking
from nz_industry_benchmarking.revision.config import RevisionConfig


def test_supported_python_version() -> None:
    """The project requires Python 3.11 or newer."""
    assert sys.version_info >= (3, 11)


def test_package_exposes_version() -> None:
    """The package version is available after a source-layout import."""
    assert nz_industry_benchmarking.__version__ == "0.1.0"


def test_environment_configuration_propagates_across_pipeline() -> None:
    """One environment mapping configures every composed pipeline layer."""
    environment = {
        "AES_SOURCE_FILE": "fixtures/new-release.csv",
        "AES_SOURCE_URL": "https://www.stats.govt.nz/new-release.csv",
        "AES_DATASET_YEAR": "2026",
        "AES_DATASET_VERSION": "2026-provisional",
        "AES_INGESTION_MANIFEST": "state/manifest.json",
        "BRONZE_TABLE_PATH": "state/bronze",
        "SILVER_TABLE_PATH": "state/silver",
        "GOLD_METRICS_PATH": "state/gold",
        "REVISION_REPORT_DIR": "state/revisions",
        "SPARK_MASTER": "local[1]",
        "SPARK_LOG_LEVEL": "ERROR",
    }

    config = RevisionConfig.from_environment(environment)

    assert config.pipeline.ingestion.source_file.as_posix() == (
        "fixtures/new-release.csv"
    )
    assert config.pipeline.ingestion.dataset_year == 2026
    assert config.pipeline.ingestion.dataset_version == "2026-provisional"
    assert config.pipeline.bronze.table_path.as_posix() == "state/bronze"
    assert config.pipeline.silver.silver_path.as_posix() == "state/silver"
    assert config.pipeline.gold.gold_metrics_path.as_posix() == "state/gold"
    assert config.pipeline.gold.spark_master == "local[1]"
    assert config.pipeline.gold.spark_log_level == "ERROR"
    assert config.report_dir.as_posix() == "state/revisions"
