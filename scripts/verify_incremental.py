"""Verify the actual AES artifact produces a fully current no-op plan."""

from __future__ import annotations

import json

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.service import run_incremental_pipeline


def main() -> None:
    """Run the incremental command and assert no actual layer is rewritten."""
    config = IncrementalConfig.from_environment()
    spark = create_spark_session(
        master=config.bronze.spark_master,
        app_name="nz-industry-benchmarking-verify-incremental",
    )
    spark.sparkContext.setLogLevel(config.bronze.spark_log_level)
    try:
        result = run_incremental_pipeline(spark, config)
        assert result.initial_plan.pipeline_status == "NO_OP"
        assert result.initial_plan.artifact_status == "ALREADY_PROCESSED"
        assert result.bronze_result is None
        assert result.silver_result is None
        assert result.gold_result is None
        print(json.dumps(result.to_dict(), indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
