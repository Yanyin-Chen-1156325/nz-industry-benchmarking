"""Command-line entry point for writing the AES Bronze Delta table."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.bronze.errors import BronzeError
from nz_industry_benchmarking.bronze.service import persist_ingestion
from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.errors import IngestionError
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)
from nz_industry_benchmarking.ingestion.service import ingest


def build_parser(
    ingestion_defaults: IngestionConfig,
    bronze_defaults: BronzeConfig,
) -> argparse.ArgumentParser:
    """Create CLI arguments from ingestion and Bronze defaults."""
    parser = argparse.ArgumentParser(
        description="Write AES source rows to Bronze Delta."
    )
    parser.add_argument(
        "--source-file", type=Path, default=ingestion_defaults.source_file
    )
    parser.add_argument("--source-url", default=ingestion_defaults.source_url)
    parser.add_argument(
        "--dataset-year", type=int, default=ingestion_defaults.dataset_year
    )
    parser.add_argument("--dataset-version", default=ingestion_defaults.dataset_version)
    parser.add_argument("--schema-version", default=ingestion_defaults.schema_version)
    parser.add_argument(
        "--manifest-file", type=Path, default=ingestion_defaults.manifest_file
    )
    parser.add_argument("--bronze-path", type=Path, default=bronze_defaults.table_path)
    parser.add_argument("--spark-master", default=bronze_defaults.spark_master)
    parser.add_argument("--spark-log-level", default=bronze_defaults.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ingest the configured CSV and idempotently persist it to Delta."""
    ingestion_defaults = IngestionConfig.from_environment()
    bronze_defaults = BronzeConfig.from_environment()
    arguments = build_parser(ingestion_defaults, bronze_defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    ingestion_config = IngestionConfig(
        source_file=arguments.source_file,
        source_url=arguments.source_url,
        dataset_year=arguments.dataset_year,
        dataset_version=arguments.dataset_version,
        schema_version=arguments.schema_version,
        manifest_file=arguments.manifest_file,
    )
    bronze_config = BronzeConfig(
        table_path=arguments.bronze_path,
        spark_master=arguments.spark_master,
        spark_log_level=arguments.spark_log_level,
    )
    spark = None
    try:
        outcome = ingest(ingestion_config)
        spark = create_spark_session(master=bronze_config.spark_master)
        spark.sparkContext.setLogLevel(bronze_config.spark_log_level)
        result = persist_ingestion(spark, outcome, bronze_config)
    except (BronzeError, IngestionError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).exception("bronze_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if spark is not None:
            spark.stop()

    print(json.dumps(result.to_dict(), indent=2))
    return 0
