"""Deterministic PySpark implementation of the approved M1-M7 contract."""

from __future__ import annotations

from datetime import UTC, datetime

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

from nz_industry_benchmarking.gold.contract import (
    DERIVED_METRICS,
    DIRECT_METRICS,
    GOLD_SCHEMA_VERSION,
    DerivedMetricSpec,
    DirectMetricSpec,
)
from nz_industry_benchmarking.gold.errors import GoldSchemaError
from nz_industry_benchmarking.quality.contract import SILVER_COLUMN_TYPES
from nz_industry_benchmarking.silver.contract import (
    VALUE_DECIMAL_PRECISION,
    VALUE_DECIMAL_SCALE,
)

IDENTITY_COLUMNS = (
    "year",
    "industry_aggregation_nzsioc",
    "industry_code_nzsioc",
)
VALUE_DECIMAL = DecimalType(VALUE_DECIMAL_PRECISION, VALUE_DECIMAL_SCALE)
ARRAY_STRING = "array<string>"


def validate_silver_schema(dataframe: DataFrame) -> None:
    """Require the complete Phase 6 Silver column/type contract."""
    actual_types = {
        field.name: field.dataType.simpleString() for field in dataframe.schema.fields
    }
    missing = sorted(set(SILVER_COLUMN_TYPES) - set(actual_types))
    unexpected = sorted(set(actual_types) - set(SILVER_COLUMN_TYPES))
    mismatches = {
        column: {
            "expected": expected,
            "actual": actual_types.get(column),
        }
        for column, expected in SILVER_COLUMN_TYPES.items()
        if column in actual_types and actual_types[column] != expected
    }
    if missing or unexpected or mismatches:
        raise GoldSchemaError(
            "Silver schema does not match the implemented contract. "
            f"Missing={missing!r}; unexpected={unexpected!r}; "
            f"types={mismatches!r}."
        )


def transform_silver_to_gold(
    silver: DataFrame,
    *,
    input_fingerprint: str,
    processing_timestamp: datetime,
) -> DataFrame:
    """Produce one M1-M6 row per observed industry/year; status implements M7."""
    validate_silver_schema(silver)
    timestamp = _normalise_timestamp(processing_timestamp)
    scaffold = _build_observation_scaffold(silver)

    direct_frames = [
        _build_direct_metric(scaffold, silver, spec) for spec in DIRECT_METRICS
    ]
    direct = _union_all(direct_frames)
    derived_frames = [
        _build_derived_metric(direct, spec) for spec in DERIVED_METRICS
    ]
    metrics = _union_all([direct, *derived_frames])

    return metrics.select(
        F.sha2(
            F.concat_ws(
                "|",
                F.lit(input_fingerprint),
                F.coalesce(F.col("year").cast("string"), F.lit("<null>")),
                F.col("industry_aggregation_nzsioc"),
                F.col("industry_code_nzsioc"),
                F.col("metric_id"),
            ),
            256,
        ).alias("metric_record_id"),
        "year",
        "industry_aggregation_nzsioc",
        "industry_code_nzsioc",
        "industry_name_nzsioc",
        "industry_code_anzsic06",
        "metric_id",
        "metric_name",
        "metric_type",
        F.col("metric_value").cast(VALUE_DECIMAL).alias("metric_value"),
        "metric_unit",
        "metric_status",
        "source_variable_code",
        "source_variable_name",
        "source_variable_category",
        "source_variable_units",
        "current_input_status",
        F.col("current_input_value").cast(VALUE_DECIMAL).alias(
            "current_input_value"
        ),
        "current_input_record_ids",
        "prior_input_status",
        F.col("prior_input_value").cast(VALUE_DECIMAL).alias("prior_input_value"),
        "prior_input_record_ids",
        "source_silver_record_ids",
        "source_ingestion_ids",
        "source_sha256s",
        "silver_input_fingerprints",
        F.lit(GOLD_SCHEMA_VERSION).alias("gold_schema_version"),
        F.lit(input_fingerprint).alias("gold_input_fingerprint"),
        F.lit(timestamp).cast("timestamp").alias("gold_processing_timestamp"),
    )


def _build_observation_scaffold(silver: DataFrame) -> DataFrame:
    return silver.groupBy(*IDENTITY_COLUMNS).agg(
        F.min("industry_name_nzsioc").alias("industry_name_nzsioc"),
        F.min("industry_code_anzsic06").alias("industry_code_anzsic06"),
        F.countDistinct(
            F.struct("industry_name_nzsioc", "industry_code_anzsic06")
        ).alias("_dimension_definition_count"),
        F.sort_array(F.collect_set("silver_input_fingerprint")).alias(
            "silver_input_fingerprints"
        ),
    )


def _build_direct_metric(
    scaffold: DataFrame,
    silver: DataFrame,
    spec: DirectMetricSpec,
) -> DataFrame:
    metadata_matches = (
        (F.col("variable_name") == spec.variable_name)
        & (F.col("variable_category") == spec.variable_category)
        & (F.col("units") == spec.source_units)
    )
    source = (
        silver.where(F.col("variable_code") == spec.variable_code)
        .groupBy(*IDENTITY_COLUMNS)
        .agg(
            F.count(F.lit(1)).alias("_source_count"),
            F.sum(F.when(metadata_matches, F.lit(1)).otherwise(F.lit(0))).alias(
                "_metadata_match_count"
            ),
            F.min(F.col("is_valid").cast("int")).alias("_input_is_valid"),
            F.min("value_status").alias("_silver_value_status"),
            F.min("value_numeric").alias("_silver_value_numeric"),
            F.sort_array(F.collect_set("record_id")).alias(
                "_current_input_record_ids"
            ),
            F.sort_array(F.collect_set("ingestion_id")).alias(
                "_source_ingestion_ids"
            ),
            F.sort_array(F.collect_set("source_sha256")).alias("_source_sha256s"),
        )
    )
    joined = scaffold.join(source, list(IDENTITY_COLUMNS), "left")
    source_count = F.coalesce(F.col("_source_count"), F.lit(0))
    status = (
        F.when(F.col("_dimension_definition_count") != 1, "INVALID_VALUE")
        .when(source_count == 0, "UNAVAILABLE")
        .when(source_count > 1, "INVALID_DUPLICATE")
        .when(F.col("_metadata_match_count") != 1, "INVALID_VALUE")
        .when(F.col("_silver_value_status") == "CONFIDENTIAL", "CONFIDENTIAL")
        .when(F.col("_silver_value_status") == "SUPPRESSED", "SUPPRESSED")
        .when(F.col("_silver_value_status") == "UNAVAILABLE", "UNAVAILABLE")
        .when(
            (F.col("_silver_value_status") == "PUBLISHED")
            & (F.col("_input_is_valid") == 1)
            & F.col("_silver_value_numeric").isNotNull(),
            "PUBLISHED",
        )
        .otherwise("INVALID_VALUE")
    )
    value = F.when(status == "PUBLISHED", F.col("_silver_value_numeric")).otherwise(
        F.lit(None).cast(VALUE_DECIMAL)
    )
    current_records = F.coalesce(
        F.col("_current_input_record_ids"), _empty_string_array()
    )
    ingestion_ids = F.coalesce(F.col("_source_ingestion_ids"), _empty_string_array())
    source_hashes = F.coalesce(F.col("_source_sha256s"), _empty_string_array())

    return joined.select(
        *IDENTITY_COLUMNS,
        "industry_name_nzsioc",
        "industry_code_anzsic06",
        F.lit(spec.metric_id).alias("metric_id"),
        F.lit(spec.metric_name).alias("metric_name"),
        F.lit("DIRECT").alias("metric_type"),
        value.alias("metric_value"),
        F.lit(spec.metric_unit).alias("metric_unit"),
        status.alias("metric_status"),
        F.lit(spec.variable_code).alias("source_variable_code"),
        F.lit(spec.variable_name).alias("source_variable_name"),
        F.lit(spec.variable_category).alias("source_variable_category"),
        F.lit(spec.source_units).alias("source_variable_units"),
        status.alias("current_input_status"),
        value.alias("current_input_value"),
        current_records.alias("current_input_record_ids"),
        F.lit(None).cast("string").alias("prior_input_status"),
        F.lit(None).cast(VALUE_DECIMAL).alias("prior_input_value"),
        _empty_string_array().alias("prior_input_record_ids"),
        current_records.alias("source_silver_record_ids"),
        ingestion_ids.alias("source_ingestion_ids"),
        source_hashes.alias("source_sha256s"),
        "silver_input_fingerprints",
    )


def _build_derived_metric(
    direct: DataFrame,
    spec: DerivedMetricSpec,
) -> DataFrame:
    source = direct.where(F.col("metric_id") == spec.source_metric_id)
    current = source.alias("current")
    prior = source.alias("prior")
    join_condition = (
        (F.col("prior.year") == F.col("current.year") - F.lit(1))
        & (
            F.col("prior.industry_aggregation_nzsioc")
            == F.col("current.industry_aggregation_nzsioc")
        )
        & (
            F.col("prior.industry_code_nzsioc")
            == F.col("current.industry_code_nzsioc")
        )
    )
    joined = current.join(prior, join_condition, "left")
    current_status = F.col("current.metric_status")
    prior_status = F.coalesce(F.col("prior.metric_status"), F.lit("UNAVAILABLE"))
    current_value = F.col("current.metric_value")
    prior_value = F.col("prior.metric_value")
    both_published = (current_status == "PUBLISHED") & (prior_status == "PUBLISHED")

    if spec.metric_id == "M4":
        status = (
            F.when(~both_published, "UNAVAILABLE_INPUT")
            .when(prior_value <= 0, "NOT_MEANINGFUL_BASE")
            .otherwise("PUBLISHED")
        )
        # All inspected AES values are integer-valued and far below 2**53, so
        # double preserves the actual source integers while avoiding Spark's
        # max-precision decimal division scale reduction.
        current_calculation = current_value.cast("double")
        prior_calculation = prior_value.cast("double")
        calculated = (
            (current_calculation - prior_calculation) * F.lit(100)
        ) / prior_calculation
    else:
        status = F.when(~both_published, "UNAVAILABLE_INPUT").otherwise("PUBLISHED")
        calculated = current_value - prior_value

    value = F.when(status == "PUBLISHED", calculated.cast(VALUE_DECIMAL)).otherwise(
        F.lit(None).cast(VALUE_DECIMAL)
    )
    current_records = F.col("current.current_input_record_ids")
    prior_records = F.coalesce(
        F.col("prior.current_input_record_ids"), _empty_string_array()
    )
    source_records = F.array_union(current_records, prior_records)
    ingestion_ids = F.array_union(
        F.col("current.source_ingestion_ids"),
        F.coalesce(F.col("prior.source_ingestion_ids"), _empty_string_array()),
    )
    source_hashes = F.array_union(
        F.col("current.source_sha256s"),
        F.coalesce(F.col("prior.source_sha256s"), _empty_string_array()),
    )
    fingerprints = F.array_union(
        F.col("current.silver_input_fingerprints"),
        F.coalesce(
            F.col("prior.silver_input_fingerprints"), _empty_string_array()
        ),
    )

    return joined.select(
        F.col("current.year").alias("year"),
        F.col("current.industry_aggregation_nzsioc").alias(
            "industry_aggregation_nzsioc"
        ),
        F.col("current.industry_code_nzsioc").alias("industry_code_nzsioc"),
        F.col("current.industry_name_nzsioc").alias("industry_name_nzsioc"),
        F.col("current.industry_code_anzsic06").alias("industry_code_anzsic06"),
        F.lit(spec.metric_id).alias("metric_id"),
        F.lit(spec.metric_name).alias("metric_name"),
        F.lit("DERIVED").alias("metric_type"),
        value.alias("metric_value"),
        F.lit(spec.metric_unit).alias("metric_unit"),
        status.alias("metric_status"),
        F.col("current.source_variable_code").alias("source_variable_code"),
        F.col("current.source_variable_name").alias("source_variable_name"),
        F.col("current.source_variable_category").alias(
            "source_variable_category"
        ),
        F.col("current.source_variable_units").alias("source_variable_units"),
        current_status.alias("current_input_status"),
        current_value.alias("current_input_value"),
        current_records.alias("current_input_record_ids"),
        prior_status.alias("prior_input_status"),
        prior_value.alias("prior_input_value"),
        prior_records.alias("prior_input_record_ids"),
        source_records.alias("source_silver_record_ids"),
        ingestion_ids.alias("source_ingestion_ids"),
        source_hashes.alias("source_sha256s"),
        fingerprints.alias("silver_input_fingerprints"),
    )


def _empty_string_array() -> Column:
    return F.array().cast(ARRAY_STRING)


def _union_all(dataframes: list[DataFrame]) -> DataFrame:
    first, *remaining = dataframes
    result = first
    for dataframe in remaining:
        result = result.unionByName(dataframe)
    return result


def _normalise_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Gold processing timestamp must be timezone-aware.")
    return value.astimezone(UTC).replace(tzinfo=None)
