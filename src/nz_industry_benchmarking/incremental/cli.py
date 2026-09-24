"""Command-line entry point for Phase 9 incremental processing."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from nz_industry_benchmarking.bronze.errors import BronzeError
from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.gold.errors import GoldError
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.errors import IncrementalError
from nz_industry_benchmarking.incremental.service import run_incremental_pipeline
from nz_industry_benchmarking.ingestion.errors import IngestionError
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)
from nz_industry_benchmarking.silver.errors import SilverError


def build_parser(defaults: IncrementalConfig) -> argparse.ArgumentParser:
    """Create a focused pipeline parser using existing configuration defaults."""
    parser = argparse.ArgumentParser(
        description="Plan and safely run the incremental AES pipeline."
    )
    parser.add_argument(
        "--source-file", type=Path, default=defaults.ingestion.source_file
    )
    parser.add_argument("--source-url", default=defaults.ingestion.source_url)
    parser.add_argument(
        "--dataset-year", type=int, default=defaults.ingestion.dataset_year
    )
    parser.add_argument(
        "--dataset-version", default=defaults.ingestion.dataset_version
    )
    parser.add_argument(
        "--manifest-file", type=Path, default=defaults.ingestion.manifest_file
    )
    parser.add_argument("--spark-master", default=defaults.bronze.spark_master)
    parser.add_argument("--spark-log-level", default=defaults.bronze.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a safe incremental run and print its complete decision record."""
    defaults = IncrementalConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    ingestion = replace(
        defaults.ingestion,
        source_file=arguments.source_file,
        source_url=arguments.source_url,
        dataset_year=arguments.dataset_year,
        dataset_version=arguments.dataset_version,
        manifest_file=arguments.manifest_file,
    )
    config = IncrementalConfig(
        ingestion=ingestion,
        bronze=replace(defaults.bronze, spark_master=arguments.spark_master),
        silver=replace(defaults.silver, spark_master=arguments.spark_master),
        gold=replace(defaults.gold, spark_master=arguments.spark_master),
    )
    spark = None
    try:
        spark = create_spark_session(
            master=arguments.spark_master,
            app_name="nz-industry-benchmarking-incremental",
        )
        spark.sparkContext.setLogLevel(arguments.spark_log_level)
        result = run_incremental_pipeline(spark, config)
    except (
        BronzeError,
        GoldError,
        IncrementalError,
        IngestionError,
        SilverError,
        OSError,
        ValueError,
    ) as error:
        logging.getLogger(LOGGER_NAME).exception("incremental_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if spark is not None:
            spark.stop()

    print(json.dumps(result.to_dict(), indent=2))
    return 0
