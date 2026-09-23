"""Integration tests for raw loading plus manifest registration."""

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from nz_industry_benchmarking.ingestion.cli import main
from nz_industry_benchmarking.ingestion.config import IngestionConfig
from nz_industry_benchmarking.ingestion.logging_config import JsonFormatter
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS
from nz_industry_benchmarking.ingestion.service import ingest


def write_source(path: Path) -> None:
    """Write two raw rows containing numeric and protected source values."""
    rows = [
        [
            "2025",
            "Level 1",
            "99999",
            "All industries",
            "Dollars (millions)",
            "H01",
            "Total income",
            "Financial performance",
            "976077",
            "ANZSIC06 divisions A-S",
        ],
        [
            "2025",
            "Level 4",
            "CC521",
            "Basic Chemical and Basic Polymer Manufacturing",
            "Dollars (millions)",
            "H23",
            "Surplus before income tax",
            "Financial performance",
            "C",
            "ANZSIC06 group C181",
        ],
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(rows)


def test_ingestion_captures_metadata_and_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "aes.csv"
    manifest = tmp_path / "manifest.json"
    write_source(source)
    config = IngestionConfig(
        source_file=source,
        source_url="https://www.stats.govt.nz/aes.csv",
        dataset_year=2025,
        dataset_version="2025-financial-year-provisional",
        schema_version="aes-public-csv-v1",
        manifest_file=manifest,
    )

    first = ingest(
        config,
        clock=lambda: datetime(2026, 9, 23, 1, 2, 3, tzinfo=UTC),
    )
    second = ingest(
        config,
        clock=lambda: datetime(2026, 9, 24, 1, 2, 3, tzinfo=UTC),
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert first.metadata == second.metadata
    assert first.metadata.source_file == source.as_posix()
    assert first.metadata.source_url == "https://www.stats.govt.nz/aes.csv"
    assert first.metadata.dataset_year == 2025
    assert first.metadata.dataset_version == "2025-financial-year-provisional"
    assert first.metadata.ingestion_timestamp == "2026-09-23T01:02:03Z"
    assert first.metadata.row_count == 2
    assert first.metadata.schema_version == "aes-public-csv-v1"
    assert first.dataset.rows[1]["Value"] == "C"
    assert len(json.loads(manifest.read_text())["ingestions"]) == 1


def test_json_formatter_emits_structured_fields() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="source_loaded",
        args=(),
        exc_info=None,
    )
    record.source_file = "data/raw/aes.csv"
    record.row_count = 2

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "source_loaded"
    assert payload["source_file"] == "data/raw/aes.csv"
    assert payload["row_count"] == 2


def test_cli_fails_clearly_for_missing_source(
    tmp_path: Path,
    capsys,
) -> None:
    missing_source = tmp_path / "missing.csv"

    exit_code = main(
        [
            "--source-file",
            str(missing_source),
            "--manifest-file",
            str(tmp_path / "manifest.json"),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["status"] == "failed"
    assert "does not exist" in output["error"]
