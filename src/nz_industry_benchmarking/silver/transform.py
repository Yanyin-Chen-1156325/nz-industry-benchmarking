"""Deterministic PySpark transformation from Bronze to Silver."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from functools import reduce
from operator import or_

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

from nz_industry_benchmarking.bronze.schema import BRONZE_SCHEMA
from nz_industry_benchmarking.silver.contract import (
    EXPECTED_AGGREGATION_LEVELS,
    EXPECTED_VARIABLE_DEFINITIONS,
    SILVER_SCHEMA_VERSION,
    VALUE_DECIMAL_PRECISION,
    VALUE_DECIMAL_SCALE,
)
from nz_industry_benchmarking.silver.errors import SilverSchemaError

NUMERIC_PATTERN = r"^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$"


def validate_bronze_schema(dataframe: DataFrame) -> None:
    """Require the exact implemented Bronze columns and logical types."""
    expected_columns = [field.name for field in BRONZE_SCHEMA.fields]
    if dataframe.columns != expected_columns:
        raise SilverSchemaError(
            "Bronze columns do not match the Phase 4 contract. "
            f"Expected {expected_columns!r}; received {dataframe.columns!r}."
        )

    expected_types = {
        field.name: field.dataType.simpleString() for field in BRONZE_SCHEMA.fields
    }
    actual_types = {
        field.name: field.dataType.simpleString() for field in dataframe.schema.fields
    }
    if actual_types != expected_types:
        raise SilverSchemaError(
            "Bronze types do not match the Phase 4 contract. "
            f"Expected {expected_types!r}; received {actual_types!r}."
        )


def transform_bronze_to_silver(
    bronze: DataFrame,
    *,
    input_fingerprint: str,
    processing_timestamp: datetime,
) -> DataFrame:
    """Type, classify, and validate every Bronze row without filtering."""
    validate_bronze_schema(bronze)
    normalized_timestamp = _normalise_timestamp(processing_timestamp)
    decimal_type = DecimalType(VALUE_DECIMAL_PRECISION, VALUE_DECIMAL_SCALE)

    value_is_blank = _is_blank("Value")
    numeric_format = F.col("Value").rlike(NUMERIC_PATTERN)
    numeric_candidate = F.expr(
        "try_cast(regexp_replace(Value, ',', '') as decimal(38,18))"
    )
    numeric_is_valid = numeric_format & numeric_candidate.isNotNull()

    value_status = (
        F.when(value_is_blank, F.lit("UNAVAILABLE"))
        .when(F.col("Value") == "C", F.lit("CONFIDENTIAL"))
        .when(F.col("Value") == "S", F.lit("SUPPRESSED"))
        .when(numeric_is_valid, F.lit("PUBLISHED"))
        .otherwise(F.lit("INVALID"))
    )

    observation_window = Window.partitionBy(
        "ingestion_id",
        "Year",
        "Industry_aggregation_NZSIOC",
        "Industry_code_NZSIOC",
        "Variable_code",
    )
    source_row_window = Window.partitionBy("ingestion_id", "source_row_number")
    ingestion_window = Window.partitionBy("ingestion_id")

    staged = (
        bronze.withColumn("_value_numeric", numeric_candidate)
        .withColumn("_value_status", value_status)
        .withColumn("_observation_count", F.count(F.lit(1)).over(observation_window))
        .withColumn("_source_row_count", F.count(F.lit(1)).over(source_row_window))
        .withColumn("_ingestion_count", F.count(F.lit(1)).over(ingestion_window))
    )

    variable_fields_present = ~(
        _is_blank("Variable_code")
        | _is_blank("Variable_name")
        | _is_blank("Variable_category")
        | _is_blank("Units")
    )
    variable_definition_valid = _variable_definition_condition()
    lineage_missing = (
        _is_blank("ingestion_id")
        | _is_blank("source_file")
        | _is_blank("source_url")
        | _is_blank("source_sha256")
        | _is_blank("dataset_version")
        | _is_blank("schema_version")
        | F.col("dataset_year").isNull()
        | F.col("ingestion_timestamp").isNull()
        | F.col("row_count").isNull()
        | F.col("source_row_number").isNull()
    )

    validations = (
        (_is_blank("Year"), "YEAR_REQUIRED", "Year is null or blank."),
        (
            (~_is_blank("Year")) & ~F.col("Year").rlike(r"^\d{4}$"),
            "YEAR_INVALID_FORMAT",
            "Year must be four numeric digits.",
        ),
        (
            _is_blank("Industry_aggregation_NZSIOC"),
            "INDUSTRY_AGGREGATION_REQUIRED",
            "Industry aggregation level is null or blank.",
        ),
        (
            (~_is_blank("Industry_aggregation_NZSIOC"))
            & ~F.col("Industry_aggregation_NZSIOC").isin(
                *EXPECTED_AGGREGATION_LEVELS
            ),
            "INDUSTRY_AGGREGATION_UNEXPECTED",
            "Industry aggregation level is outside the Phase 0 contract.",
        ),
        (
            _is_blank("Industry_code_NZSIOC"),
            "INDUSTRY_CODE_REQUIRED",
            "NZSIOC industry code is null or blank.",
        ),
        (
            _is_blank("Industry_name_NZSIOC"),
            "INDUSTRY_NAME_REQUIRED",
            "NZSIOC industry name is null or blank.",
        ),
        (
            _is_blank("Industry_code_ANZSIC06"),
            "ANZSIC_MAPPING_REQUIRED",
            "ANZSIC06 mapping is null or blank.",
        ),
        (
            _is_blank("Variable_code"),
            "VARIABLE_CODE_REQUIRED",
            "Variable code is null or blank.",
        ),
        (
            _is_blank("Variable_name"),
            "VARIABLE_NAME_REQUIRED",
            "Variable name is null or blank.",
        ),
        (
            _is_blank("Variable_category"),
            "VARIABLE_CATEGORY_REQUIRED",
            "Variable category is null or blank.",
        ),
        (_is_blank("Units"), "UNITS_REQUIRED", "Units are null or blank."),
        (
            variable_fields_present & ~variable_definition_valid,
            "VARIABLE_DEFINITION_UNEXPECTED",
            "Code, name, category, and units do not match a Phase 0 definition.",
        ),
        (
            F.col("_value_status") == "UNAVAILABLE",
            "VALUE_UNAVAILABLE",
            "Source Value is null, empty, or whitespace-only.",
        ),
        (
            F.col("_value_status") == "INVALID",
            "VALUE_INVALID",
            "Source Value is neither numeric text nor C or S.",
        ),
        (
            F.col("_observation_count") > 1,
            "OBSERVATION_DUPLICATE",
            "Observation identity is duplicated within an ingestion.",
        ),
        (
            lineage_missing,
            "LINEAGE_REQUIRED",
            "One or more required Bronze lineage fields are unavailable.",
        ),
        (
            (~_is_blank("ingestion_id"))
            & (~_is_blank("source_sha256"))
            & (F.col("ingestion_id") != F.col("source_sha256")),
            "LINEAGE_ID_MISMATCH",
            "Ingestion ID does not equal the source SHA-256.",
        ),
        (
            F.col("source_row_number").isNotNull()
            & F.col("row_count").isNotNull()
            & (
                (F.col("source_row_number") < 1)
                | (F.col("source_row_number") > F.col("row_count"))
            ),
            "SOURCE_ROW_NUMBER_INVALID",
            "Source row number is outside the captured source row count.",
        ),
        (
            F.col("_source_row_count") > 1,
            "SOURCE_ROW_NUMBER_DUPLICATE",
            "Source row number is duplicated within an ingestion.",
        ),
        (
            F.col("row_count").isNotNull()
            & (F.col("_ingestion_count") != F.col("row_count")),
            "SOURCE_ROW_COUNT_MISMATCH",
            "Stored ingestion rows do not match Bronze row_count metadata.",
        ),
    )

    rule_ids = _compact_validation_array(
        F.when(condition, F.lit(rule_id))
        for condition, rule_id, _ in validations
    )
    failure_reasons = _compact_validation_array(
        F.when(condition, F.lit(reason))
        for condition, _, reason in validations
    )

    validated = (
        staged.withColumn("validation_rule_ids", rule_ids)
        .withColumn("validation_failure_reasons", failure_reasons)
        .withColumn("is_valid", F.size("validation_rule_ids") == 0)
    )

    return validated.select(
        F.concat_ws(":", "ingestion_id", F.col("source_row_number")).alias(
            "record_id"
        ),
        F.col("Year").cast("integer").alias("year"),
        F.col("Year").alias("year_raw"),
        F.col("Industry_aggregation_NZSIOC").alias(
            "industry_aggregation_nzsioc"
        ),
        F.col("Industry_code_NZSIOC").alias("industry_code_nzsioc"),
        F.col("Industry_name_NZSIOC").alias("industry_name_nzsioc"),
        F.col("Industry_code_ANZSIC06").alias("industry_code_anzsic06"),
        F.col("Variable_code").alias("variable_code"),
        F.col("Variable_name").alias("variable_name"),
        F.col("Variable_category").alias("variable_category"),
        F.col("Units").alias("units"),
        F.col("Value").alias("value_raw"),
        F.when(F.col("_value_status") == "PUBLISHED", F.col("_value_numeric"))
        .otherwise(F.lit(None).cast(decimal_type))
        .alias("value_numeric"),
        F.col("_value_status").alias("value_status"),
        F.when(F.col("is_valid"), F.lit("VALID"))
        .otherwise(F.lit("INVALID"))
        .alias("record_status"),
        "is_valid",
        "validation_rule_ids",
        "validation_failure_reasons",
        "ingestion_id",
        "source_file",
        "source_url",
        "source_sha256",
        "dataset_year",
        "dataset_version",
        "ingestion_timestamp",
        F.col("row_count").alias("source_row_count"),
        F.col("schema_version").alias("source_schema_version"),
        "source_row_number",
        F.lit(SILVER_SCHEMA_VERSION).alias("silver_schema_version"),
        F.lit(input_fingerprint).alias("silver_input_fingerprint"),
        F.lit(normalized_timestamp).cast("timestamp").alias(
            "silver_processing_timestamp"
        ),
    )


def _is_blank(column: str) -> Column:
    value = F.col(column)
    return value.isNull() | (F.length(F.trim(value)) == 0)


def _variable_definition_condition() -> Column:
    conditions = (
        (F.col("Variable_code") == code)
        & (F.col("Variable_name") == name)
        & (F.col("Variable_category") == category)
        & (F.col("Units") == units)
        for code, name, category, units in EXPECTED_VARIABLE_DEFINITIONS
    )
    return reduce(or_, conditions, F.lit(False))


def _compact_validation_array(values: Iterable[Column]) -> Column:
    return F.array_compact(F.array(*values))


def _normalise_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Silver processing timestamp must be timezone-aware.")
    return value.astimezone(UTC).replace(tzinfo=None)
