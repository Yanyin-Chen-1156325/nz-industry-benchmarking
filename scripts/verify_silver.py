"""Print factual checks for the implemented Silver Delta table."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.silver.config import SilverConfig


def main() -> None:
    """Compare Silver with Bronze and report status and lineage checks."""
    config = SilverConfig.from_environment()
    spark = create_spark_session(app_name="silver-actual-verification")
    spark.sparkContext.setLogLevel("ERROR")
    try:
        bronze = spark.read.format("delta").load(
            config.bronze_path.resolve().as_uri()
        )
        silver = spark.read.format("delta").load(
            config.silver_path.resolve().as_uri()
        )
        status_counts = {
            row.value_status: row["count"]
            for row in silver.groupBy("value_status").count().collect()
        }
        lineage_mismatches = (
            silver.alias("silver")
            .join(
                bronze.alias("bronze"),
                (F.col("silver.ingestion_id") == F.col("bronze.ingestion_id"))
                & (
                    F.col("silver.source_row_number")
                    == F.col("bronze.source_row_number")
                ),
                "left",
            )
            .where(
                F.col("bronze.source_row_number").isNull()
                | (F.col("silver.value_raw") != F.col("bronze.Value"))
            )
            .count()
        )
        result = {
            "bronze_input_rows": bronze.count(),
            "silver_output_rows": silver.count(),
            "status_counts": dict(sorted(status_counts.items())),
            "valid_rows": silver.where(F.col("is_valid")).count(),
            "invalid_rows": silver.where(~F.col("is_valid")).count(),
            "published_with_null_numeric": silver.where(
                (F.col("value_status") == "PUBLISHED")
                & F.col("value_numeric").isNull()
            ).count(),
            "protected_with_numeric": silver.where(
                F.col("value_status").isin("CONFIDENTIAL", "SUPPRESSED")
                & F.col("value_numeric").isNotNull()
            ).count(),
            "negative_published_values": silver.where(
                (F.col("value_status") == "PUBLISHED")
                & (F.col("value_numeric") < 0)
            ).count(),
            "confidential_raw_mismatches": silver.where(
                (F.col("value_raw") == "C")
                & (F.col("value_status") != "CONFIDENTIAL")
            ).count(),
            "suppressed_raw_mismatches": silver.where(
                (F.col("value_raw") == "S")
                & (F.col("value_status") != "SUPPRESSED")
            ).count(),
            "lineage_or_raw_value_mismatches": lineage_mismatches,
            "processing_timestamps": silver.select(
                "silver_processing_timestamp"
            ).distinct().count(),
        }
        print(json.dumps(result, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
