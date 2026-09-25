"""Orchestration for one logical AES ingestion attempt."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.loader import load_raw_csv
from nz_industry_benchmarking.ingestion.logging_config import LOGGER_NAME
from nz_industry_benchmarking.ingestion.manifest import IngestionManifest
from nz_industry_benchmarking.ingestion.models import (
    IngestionMetadata,
    IngestionOutcome,
)

logger = logging.getLogger(LOGGER_NAME)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def ingest(
    config: IngestionConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> IngestionOutcome:
    """Load an AES CSV and register its artifact metadata exactly once."""
    started = perf_counter()
    logger.info(
        "ingestion_started",
        extra={
            "source_file": config.source_file.as_posix(),
            "source_url": config.source_url,
            "dataset_year": config.dataset_year,
            "dataset_version": config.dataset_version,
            "schema_version": config.schema_version,
        },
    )

    try:
        outcome = prepare_ingestion(config, clock=clock)
        registration = IngestionManifest(config.manifest_file).register(
            outcome.metadata
        )
        duplicate = not registration.inserted
        logger.info(
            "duplicate_ingestion_detected" if duplicate else "ingestion_registered",
            extra={
                "ingestion_id": registration.metadata.ingestion_id,
                "source_sha256": registration.metadata.source_sha256,
                "row_count": registration.metadata.row_count,
                "duplicate": duplicate,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            },
        )
        return IngestionOutcome(
            metadata=registration.metadata,
            duplicate=duplicate,
            dataset=outcome.dataset,
        )
    except Exception:
        logger.exception(
            "ingestion_failed",
            extra={
                "source_file": config.source_file.as_posix(),
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            },
        )
        raise


def prepare_ingestion(
    config: IngestionConfig,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> IngestionOutcome:
    """Load and identify a source artifact without persisting local state.

    Databricks initial-load orchestration uses this boundary because the local
    JSON manifest is not the future managed-state design. Local ingestion keeps
    registering this same candidate in its existing manifest.
    """
    dataset = load_raw_csv(config.source_file)
    logger.info(
        "source_loaded",
        extra={
            "source_file": config.source_file.as_posix(),
            "source_sha256": dataset.source_sha256,
            "row_count": dataset.row_count,
        },
    )
    metadata = IngestionMetadata(
        ingestion_id=dataset.source_sha256,
        source_file=config.source_file.as_posix(),
        source_url=config.source_url,
        source_sha256=dataset.source_sha256,
        dataset_year=config.dataset_year,
        dataset_version=config.dataset_version,
        ingestion_timestamp=_format_timestamp(clock()),
        row_count=dataset.row_count,
        schema_version=config.schema_version,
    )
    return IngestionOutcome(metadata=metadata, duplicate=False, dataset=dataset)


def _format_timestamp(value: datetime) -> str:
    """Normalize an aware datetime as an ISO-8601 UTC timestamp."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Ingestion clock must return a timezone-aware datetime.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
