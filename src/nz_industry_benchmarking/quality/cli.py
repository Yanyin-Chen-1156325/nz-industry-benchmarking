"""Command-line entry point for Silver data-quality assessment."""

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
from nz_industry_benchmarking.quality.config import QualityConfig
from nz_industry_benchmarking.quality.errors import QualityError
from nz_industry_benchmarking.quality.service import run_quality_assessment


def build_parser(defaults: QualityConfig) -> argparse.ArgumentParser:
    """Create the quality command parser from configured defaults."""
    parser = argparse.ArgumentParser(description="Assess the Silver AES Delta table.")
    parser.add_argument("--silver-path", type=Path, default=defaults.silver_path)
    parser.add_argument("--report-path", type=Path, default=defaults.report_path)
    parser.add_argument("--spark-master", default=defaults.spark_master)
    parser.add_argument("--spark-log-level", default=defaults.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the quality assessment, print its report, and signal PASS or FAIL."""
    defaults = QualityConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    config = QualityConfig(
        silver_path=arguments.silver_path,
        report_path=arguments.report_path,
        spark_master=arguments.spark_master,
        spark_log_level=arguments.spark_log_level,
    )
    spark = None
    try:
        spark = create_spark_session(
            master=config.spark_master,
            app_name="nz-industry-benchmarking-quality",
        )
        spark.sparkContext.setLogLevel(config.spark_log_level)
        report = run_quality_assessment(spark, config)
    except (QualityError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).exception("quality_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2
    finally:
        if spark is not None:
            spark.stop()

    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.overall_result == "PASS" else 1
