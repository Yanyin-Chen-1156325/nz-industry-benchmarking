"""JSON logging configuration for command-line ingestion runs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "nz_industry_benchmarking.ingestion"
STRUCTURED_FIELDS = (
    "source_file",
    "source_url",
    "source_sha256",
    "dataset_year",
    "dataset_version",
    "schema_version",
    "row_count",
    "ingestion_id",
    "duplicate",
    "duration_ms",
    "bronze_path",
    "inserted_rows",
    "total_rows",
    "silver_path",
    "valid_rows",
    "invalid_rows",
    "quality_report_path",
    "quality_result",
    "failed_checks",
    "gold_path",
    "pipeline_status",
    "artifact_status",
    "bronze_action",
    "silver_action",
    "gold_action",
    "revision_sensitive",
    "overlap_observations",
    "changed_observations",
)


class JsonFormatter(logging.Formatter):
    """Format an ingestion log record as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for field in STRUCTURED_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_structured_logging(level: str = "INFO") -> None:
    """Configure the ingestion logger without changing unrelated loggers."""
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
