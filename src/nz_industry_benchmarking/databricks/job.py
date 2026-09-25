"""Console entry point for a Databricks Python wheel task."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pyspark.sql import SparkSession

from nz_industry_benchmarking.databricks.config import (
    DEFAULT_BRONZE_TABLE,
    DEFAULT_CATALOG,
    DEFAULT_DATABRICKS_SCHEMA,
    DEFAULT_GOLD_TABLE,
    DEFAULT_SILVER_TABLE,
    DatabricksInitialLoadConfig,
)
from nz_industry_benchmarking.databricks.pipeline import run_initial_load


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse Databricks wheel-task parameters."""
    parser = argparse.ArgumentParser(
        description="Run the initial Databricks Bronze-to-Gold AES load."
    )
    parser.add_argument(
        "--source-file",
        required=True,
        type=Path,
        help="Unity Catalog Volume path to the Stats NZ CSV.",
    )
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--schema", default=DEFAULT_DATABRICKS_SCHEMA)
    parser.add_argument("--bronze-table", default=DEFAULT_BRONZE_TABLE)
    parser.add_argument("--silver-table", default=DEFAULT_SILVER_TABLE)
    parser.add_argument("--gold-table", default=DEFAULT_GOLD_TABLE)
    return parser.parse_args(argv)


def require_active_spark_session() -> SparkSession:
    """Return the Databricks-owned active session without creating one."""
    spark = SparkSession.getActiveSession()
    if spark is None:
        raise RuntimeError(
            "No active SparkSession is available. Run this entry point as a "
            "Databricks Python wheel task on a Spark-enabled runtime."
        )
    return spark


def main(argv: Sequence[str] | None = None) -> None:
    """Delegate one configured wheel-task invocation to shared orchestration."""
    args = parse_arguments(argv)
    spark = require_active_spark_session()
    config = DatabricksInitialLoadConfig(
        source_file=args.source_file,
        catalog=args.catalog,
        schema=args.schema,
        bronze_table=args.bronze_table,
        silver_table=args.silver_table,
        gold_table=args.gold_table,
    )
    result = run_initial_load(spark, config)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
