"""Command-line entry point for local AES ingestion."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.errors import IngestionError
from nz_industry_benchmarking.ingestion.logging_config import (
    LOGGER_NAME,
    configure_structured_logging,
)
from nz_industry_benchmarking.ingestion.service import ingest


def build_parser(defaults: IngestionConfig) -> argparse.ArgumentParser:
    """Create the ingestion argument parser using configured defaults."""
    parser = argparse.ArgumentParser(description="Ingest the public Stats NZ AES CSV.")
    parser.add_argument("--source-file", type=Path, default=defaults.source_file)
    parser.add_argument("--source-url", default=defaults.source_url)
    parser.add_argument("--dataset-year", type=int, default=defaults.dataset_year)
    parser.add_argument("--dataset-version", default=defaults.dataset_version)
    parser.add_argument("--schema-version", default=defaults.schema_version)
    parser.add_argument("--manifest-file", type=Path, default=defaults.manifest_file)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ingestion, print a JSON summary, and return a process exit code."""
    defaults = IngestionConfig.from_environment()
    arguments = build_parser(defaults).parse_args(argv)
    configure_structured_logging(arguments.log_level)
    config = IngestionConfig(
        source_file=arguments.source_file,
        source_url=arguments.source_url,
        dataset_year=arguments.dataset_year,
        dataset_version=arguments.dataset_version,
        schema_version=arguments.schema_version,
        manifest_file=arguments.manifest_file,
    )

    try:
        outcome = ingest(config)
    except (IngestionError, OSError, ValueError) as error:
        logging.getLogger(LOGGER_NAME).error(
            "ingestion_command_failed",
            extra={"source_file": config.source_file.as_posix()},
        )
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1

    print(json.dumps(outcome.summary(), indent=2))
    return 0
