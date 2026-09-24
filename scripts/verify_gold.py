"""Inspect the implemented Gold metric Delta table and acceptance examples."""

from __future__ import annotations

import json
from decimal import Decimal

from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.gold.config import GoldConfig


def main() -> int:
    """Print deterministic Gold checks and fail on contract violations."""
    config = GoldConfig.from_environment()
    spark = create_spark_session(app_name="verify-gold")
    spark.sparkContext.setLogLevel(config.spark_log_level)
    try:
        gold = spark.read.format("delta").load(
            config.gold_metrics_path.resolve().as_uri()
        )
        grain = [
            "gold_input_fingerprint",
            "year",
            "industry_aggregation_nzsioc",
            "industry_code_nzsioc",
            "metric_id",
        ]
        output_rows = gold.count()
        distinct_grain_rows = gold.select(*grain).distinct().count()
        metric_status_counts = [
            {
                "metric_id": row.metric_id,
                "metric_status": row.metric_status,
                "rows": row["count"],
            }
            for row in gold.groupBy("metric_id", "metric_status")
            .count()
            .orderBy("metric_id", "metric_status")
            .collect()
        ]
        aggregation_counts = {
            row.industry_aggregation_nzsioc: row["count"]
            for row in gold.groupBy("industry_aggregation_nzsioc").count().collect()
        }
        examples = _acceptance_examples(gold)
        protected_numeric_leaks = gold.where(
            F.col("metric_status").isin("CONFIDENTIAL", "SUPPRESSED")
            & F.col("metric_value").isNotNull()
        ).count()
        unavailable_numeric_leaks = gold.where(
            (F.col("metric_status") != "PUBLISHED")
            & F.col("metric_value").isNotNull()
        ).count()
        missing_lineage = gold.where(
            (F.size("silver_input_fingerprints") == 0)
            | F.col("gold_input_fingerprint").isNull()
            | F.col("gold_schema_version").isNull()
        ).count()
        result = {
            "gold_output_rows": output_rows,
            "distinct_grain_rows": distinct_grain_rows,
            "aggregation_counts": dict(sorted(aggregation_counts.items())),
            "metric_status_counts": metric_status_counts,
            "protected_numeric_leaks": protected_numeric_leaks,
            "unavailable_numeric_leaks": unavailable_numeric_leaks,
            "missing_lineage_rows": missing_lineage,
            "acceptance_examples": examples,
        }
        print(json.dumps(result, indent=2, default=str))
        violations = (
            output_rows != distinct_grain_rows
            or protected_numeric_leaks != 0
            or unavailable_numeric_leaks != 0
            or missing_lineage != 0
            or not all(example["verified"] for example in examples)
        )
        return 1 if violations else 0
    finally:
        spark.stop()


def _acceptance_examples(gold) -> list[dict[str, object]]:
    definitions = (
        ("M1", 2025, "Level 1", "CC", "134105.000000000000000000", "PUBLISHED"),
        ("M2", 2025, "Level 1", "EE", "6410.000000000000000000", "PUBLISHED"),
        ("M3", 2025, "Level 1", "EE", "9.000000000000000000", "PUBLISHED"),
        (
            "M4",
            2025,
            "Level 1",
            "CC",
            "5.13",
            "PUBLISHED",
        ),
        ("M5", 2025, "Level 1", "EE", "-1806.000000000000000000", "PUBLISHED"),
        ("M6", 2025, "Level 1", "EE", "-3.000000000000000000", "PUBLISHED"),
        ("M2", 2023, "Level 4", "CC521", None, "CONFIDENTIAL"),
        ("M5", 2023, "Level 4", "CC521", None, "UNAVAILABLE_INPUT"),
    )
    results = []
    for metric_id, year, level, code, expected_value, expected_status in definitions:
        row = gold.where(
            (F.col("metric_id") == metric_id)
            & (F.col("year") == year)
            & (F.col("industry_aggregation_nzsioc") == level)
            & (F.col("industry_code_nzsioc") == code)
        ).first()
        actual_value = (
            None
            if row is None or row.metric_value is None
            else str(row.metric_value)
        )
        actual_status = None if row is None else row.metric_status
        results.append(
            {
                "metric_id": metric_id,
                "year": year,
                "aggregation": level,
                "industry_code": code,
                "value": actual_value,
                "status": actual_status,
                "current_input_status": None
                if row is None
                else row.current_input_status,
                "prior_input_status": None if row is None else row.prior_input_status,
                "verified": _value_matches(metric_id, actual_value, expected_value)
                and actual_status == expected_status,
            }
        )
    return results


def _value_matches(
    metric_id: str,
    actual_value: str | None,
    expected_value: str | None,
) -> bool:
    if metric_id == "M4" and actual_value is not None and expected_value is not None:
        return Decimal(actual_value).quantize(Decimal("0.01")) == Decimal(
            expected_value
        )
    return actual_value == expected_value


if __name__ == "__main__":
    raise SystemExit(main())
