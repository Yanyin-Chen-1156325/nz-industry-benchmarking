"""Command-line entry point for read-only Gold benchmark queries."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from nz_industry_benchmarking.benchmarking.config import BenchmarkConfig
from nz_industry_benchmarking.benchmarking.contract import (
    CHANGE_METRIC_IDS,
    RANKING_TYPES,
)
from nz_industry_benchmarking.benchmarking.errors import BenchmarkError
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest
from nz_industry_benchmarking.benchmarking.service import query_benchmarks
from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)


def build_parser(defaults: BenchmarkConfig) -> argparse.ArgumentParser:
    """Create the benchmark query parser."""
    parser = argparse.ArgumentParser(
        description="Rank published Gold M4-M6 results within one year and level."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--metric-id", choices=CHANGE_METRIC_IDS, required=True)
    parser.add_argument("--aggregation-level", required=True)
    parser.add_argument("--ranking-type", choices=RANKING_TYPES, required=True)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument(
        "--gold-metrics-path", type=Path, default=defaults.gold_metrics_path
    )
    parser.add_argument("--spark-master", default=defaults.spark_master)
    parser.add_argument("--spark-log-level", default=defaults.spark_log_level)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one benchmark query and print API-friendly JSON."""
    defaults = BenchmarkConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    config = BenchmarkConfig(
        gold_metrics_path=arguments.gold_metrics_path,
        spark_master=arguments.spark_master,
        spark_log_level=arguments.spark_log_level,
    )
    spark = None
    try:
        request = BenchmarkRequest(
            year=arguments.year,
            metric_id=arguments.metric_id,
            aggregation_level=arguments.aggregation_level,
            ranking_type=arguments.ranking_type,
            top_n=arguments.top_n,
        )
        spark = create_spark_session(
            master=config.spark_master,
            app_name="nz-industry-benchmarking-rankings",
        )
        spark.sparkContext.setLogLevel(config.spark_log_level)
        rows = [
            row.asDict(recursive=True)
            for row in query_benchmarks(spark, config, request).collect()
        ]
    except (BenchmarkError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).exception("benchmark_command_failed")
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if spark is not None:
            spark.stop()

    print(
        json.dumps(
            {"request": asdict(request), "result_count": len(rows), "results": rows},
            indent=2,
            default=str,
        )
    )
    return 0
