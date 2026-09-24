"""Stable Phase 6 quality rule and Silver schema contracts."""

from __future__ import annotations

BLOCKING = "BLOCKING"
INFORMATIONAL = "INFORMATIONAL"

SILVER_COLUMN_TYPES = {
    "record_id": "string",
    "year": "int",
    "year_raw": "string",
    "industry_aggregation_nzsioc": "string",
    "industry_code_nzsioc": "string",
    "industry_name_nzsioc": "string",
    "industry_code_anzsic06": "string",
    "variable_code": "string",
    "variable_name": "string",
    "variable_category": "string",
    "units": "string",
    "value_raw": "string",
    "value_numeric": "decimal(38,18)",
    "value_status": "string",
    "record_status": "string",
    "is_valid": "boolean",
    "validation_rule_ids": "array<string>",
    "validation_failure_reasons": "array<string>",
    "ingestion_id": "string",
    "source_file": "string",
    "source_url": "string",
    "source_sha256": "string",
    "dataset_year": "int",
    "dataset_version": "string",
    "ingestion_timestamp": "timestamp",
    "source_row_count": "bigint",
    "source_schema_version": "string",
    "source_row_number": "bigint",
    "silver_schema_version": "string",
    "silver_input_fingerprint": "string",
    "silver_processing_timestamp": "timestamp",
}

QUALITY_RULES = {
    "DQ_SCHEMA_REQUIRED_COLUMNS": (
        "schema",
        BLOCKING,
        "Every implemented Silver column is present.",
    ),
    "DQ_SCHEMA_UNEXPECTED_COLUMNS": (
        "schema",
        BLOCKING,
        "No undocumented columns are present.",
    ),
    "DQ_SCHEMA_COLUMN_TYPES": (
        "schema",
        BLOCKING,
        "Silver columns use the implemented logical data types.",
    ),
    "DQ_COMPLETENESS_REQUIRED_DIMENSIONS": (
        "completeness",
        BLOCKING,
        "Required observation dimensions are populated.",
    ),
    "DQ_VALIDITY_YEAR": (
        "validity",
        BLOCKING,
        "Year is a consistent four-digit value.",
    ),
    "DQ_VALIDITY_AGGREGATION_LEVEL": (
        "validity",
        BLOCKING,
        "Aggregation level is supported by the source contract.",
    ),
    "DQ_VALIDITY_VARIABLE_DEFINITION": (
        "business_contract",
        BLOCKING,
        "Variable code, name, category, and units match an approved definition.",
    ),
    "DQ_VALIDITY_VALUE_STATE": (
        "validity",
        BLOCKING,
        "Raw, numeric, and status values agree with the Silver value contract.",
    ),
    "DQ_UNIQUENESS_RECORD_ID": (
        "uniqueness",
        BLOCKING,
        "Record identifiers are unique.",
    ),
    "DQ_UNIQUENESS_OBSERVATION_GRAIN": (
        "uniqueness",
        BLOCKING,
        "Observations are unique at the approved "
        "ingestion/year/level/industry/variable grain.",
    ),
    "DQ_CONTRACT_VALIDATION_OUTCOME": (
        "business_contract",
        BLOCKING,
        "Silver validity flags and failure arrays are internally consistent.",
    ),
    "DQ_CONTRACT_INVALID_ROWS": (
        "business_contract",
        BLOCKING,
        "Silver contains no rows rejected by its implemented validation contract.",
    ),
    "DQ_CONTRACT_LINEAGE": (
        "business_contract",
        BLOCKING,
        "Required source and processing lineage is complete and consistent.",
    ),
    "DQ_INFO_CONFIDENTIAL_ROWS": (
        "informational",
        INFORMATIONAL,
        "Count confidential source observations without treating them as failures.",
    ),
    "DQ_INFO_SUPPRESSED_ROWS": (
        "informational",
        INFORMATIONAL,
        "Count suppressed source observations without treating them as failures.",
    ),
    "DQ_INFO_NEGATIVE_PUBLISHED_ROWS": (
        "informational",
        INFORMATIONAL,
        "Count valid negative published values without treating them as failures.",
    ),
}
