"""Command-line entry point for Phase 10 revision handling."""

from __future__ import annotations

import json
from collections.abc import Sequence

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.revision.config import RevisionConfig
from nz_industry_benchmarking.revision.service import run_revision_pipeline


def main(argv: Sequence[str] | None = None) -> int:
    """Run revision handling with environment-backed existing configuration."""
    if argv:
        raise ValueError(
            "Revision CLI uses the existing environment configuration and accepts "
            "no positional arguments."
        )
    config = RevisionConfig.from_environment()
    spark = create_spark_session(
        master=config.pipeline.bronze.spark_master,
        app_name="nz-industry-benchmarking-revision",
    )
    spark.sparkContext.setLogLevel(config.pipeline.bronze.spark_log_level)
    try:
        result = run_revision_pipeline(spark, config)
        print(json.dumps(result.to_dict(), indent=2))
    finally:
        spark.stop()
    return 0
