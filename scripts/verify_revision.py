"""Verify the single actual AES release remains a safe Phase 10 no-op."""

from __future__ import annotations

import json

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.revision.config import RevisionConfig
from nz_industry_benchmarking.revision.service import run_revision_pipeline


def main() -> None:
    config = RevisionConfig.from_environment()
    spark = create_spark_session(
        master=config.pipeline.bronze.spark_master,
        app_name="nz-industry-benchmarking-verify-revision",
    )
    spark.sparkContext.setLogLevel(config.pipeline.bronze.spark_log_level)
    try:
        result = run_revision_pipeline(spark, config)
        assert result.report.overall_result == "NO_OP"
        assert result.bronze_result is None
        assert result.silver_result is None
        assert result.gold_result is None
        print(json.dumps(result.to_dict(), indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
