"""Contract for Phase 8 ranking queries over approved Gold metrics."""

CHANGE_METRIC_IDS = ("M4", "M5", "M6")
RANKING_TYPES = ("top_increases", "top_decreases", "largest_movements")

GOLD_BENCHMARK_COLUMN_TYPES = {
    "metric_record_id": "string",
    "year": "int",
    "industry_aggregation_nzsioc": "string",
    "industry_code_nzsioc": "string",
    "industry_name_nzsioc": "string",
    "metric_id": "string",
    "metric_name": "string",
    "metric_value": "decimal(38,18)",
    "metric_unit": "string",
    "metric_status": "string",
    "source_silver_record_ids": "array<string>",
    "source_ingestion_ids": "array<string>",
    "source_sha256s": "array<string>",
    "silver_input_fingerprints": "array<string>",
    "gold_schema_version": "string",
    "gold_input_fingerprint": "string",
    "gold_processing_timestamp": "timestamp",
}

BENCHMARK_OUTPUT_COLUMNS = (
    "ranking_type",
    "rank_position",
    "year",
    "industry_aggregation_nzsioc",
    "metric_id",
    "metric_name",
    "metric_unit",
    "metric_status",
    "industry_code_nzsioc",
    "industry_name_nzsioc",
    "metric_value",
    "absolute_metric_value",
    "metric_record_id",
    "source_silver_record_ids",
    "source_ingestion_ids",
    "source_sha256s",
    "silver_input_fingerprints",
    "gold_schema_version",
    "gold_input_fingerprint",
    "gold_processing_timestamp",
)
