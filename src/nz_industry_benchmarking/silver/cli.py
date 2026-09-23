"""Command-line entry point for Bronze-to-Silver processing."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)
from nz_industry_benchmarking.silver.config import SilverConfig
from nz_industry_benchmarking.silver.errors import SilverError
from nz_industry_benchmarking.silver.service import process_silver


def build_parser(defaults: SilverConfig) -> argparse.ArgumentParser:
    """Create the Silver command parser from configured defaults."""
    parser = argparse.ArgumentParser(
        description="Transform Bronze AES observations into Silver Delta."
    )
    parser.add_argument("--bronze-path", type=Path, default=defaults.bronze_path)
    parser.add_argument("--silver-path", type=Path, default=defaults.silver_path)
    parser.add_argument("--spark-master", default=defaults.spark_master)
    parser.add_argument("--spark-log-level", default=defaults.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Silver processing and print a structured summary."""
    defaults = SilverConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    config = SilverConfig(
        bronze_path=arguments.bronze_path,
        silver_path=arguments.silver_path,
        spark_master=arguments.spark_master,
        spark_log_level=arguments.spark_log_level,
    )
    spark = None
    try:
        spark = create_spark_session(master=config.spark_master)
        spark.sparkContext.setLogLevel(config.spark_log_level)
        result = process_silver(spark, config)
    except (SilverError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).exception("silver_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if spark is not None:
            spark.stop()

    print(json.dumps(result.to_dict(), indent=2))
    return 0
