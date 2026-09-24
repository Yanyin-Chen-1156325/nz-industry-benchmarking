"""Command-line entry point for Silver-to-Gold metric processing."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.gold.config import GoldConfig
from nz_industry_benchmarking.gold.errors import GoldError
from nz_industry_benchmarking.gold.service import process_gold
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)


def build_parser(defaults: GoldConfig) -> argparse.ArgumentParser:
    """Create the Gold command parser from configured defaults."""
    parser = argparse.ArgumentParser(
        description="Calculate approved M1-M7 metrics from Silver AES Delta."
    )
    parser.add_argument("--silver-path", type=Path, default=defaults.silver_path)
    parser.add_argument(
        "--gold-metrics-path", type=Path, default=defaults.gold_metrics_path
    )
    parser.add_argument("--spark-master", default=defaults.spark_master)
    parser.add_argument("--spark-log-level", default=defaults.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Gold processing and print a structured summary."""
    defaults = GoldConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    config = GoldConfig(
        silver_path=arguments.silver_path,
        gold_metrics_path=arguments.gold_metrics_path,
        spark_master=arguments.spark_master,
        spark_log_level=arguments.spark_log_level,
    )
    spark = None
    try:
        spark = create_spark_session(
            master=config.spark_master,
            app_name="nz-industry-benchmarking-gold",
        )
        spark.sparkContext.setLogLevel(config.spark_log_level)
        result = process_gold(spark, config)
    except (GoldError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).exception("gold_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if spark is not None:
            spark.stop()

    print(json.dumps(result.to_dict(), indent=2))
    return 0
