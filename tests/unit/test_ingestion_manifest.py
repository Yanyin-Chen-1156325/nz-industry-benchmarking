"""Unit tests for logical ingestion registration."""

import json
from pathlib import Path

import pytest

from nz_industry_benchmarking.ingestion.errors import ManifestError
from nz_industry_benchmarking.ingestion.manifest import IngestionManifest
from nz_industry_benchmarking.ingestion.models import IngestionMetadata


def metadata(timestamp: str = "2026-09-23T00:00:00Z") -> IngestionMetadata:
    """Build deterministic metadata for manifest tests."""
    return IngestionMetadata(
        ingestion_id="ABC123",
        source_file="data/raw/aes.csv",
        source_url="https://www.stats.govt.nz/aes.csv",
        source_sha256="ABC123",
        dataset_year=2025,
        dataset_version="2025-provisional",
        ingestion_timestamp=timestamp,
        row_count=2,
        schema_version="aes-public-csv-v1",
    )


def test_register_is_idempotent_for_same_artifact(tmp_path: Path) -> None:
    manifest = IngestionManifest(tmp_path / "manifest.json")

    first = manifest.register(metadata())
    second = manifest.register(metadata("2026-09-24T00:00:00Z"))

    assert first.inserted is True
    assert second.inserted is False
    assert second.metadata.ingestion_timestamp == "2026-09-23T00:00:00Z"
    assert len(manifest.read()) == 1


def test_manifest_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(ManifestError, match="manifest is invalid"):
        IngestionManifest(path).read()


def test_manifest_rejects_non_object_root(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ManifestError, match="root must be an object"):
        IngestionManifest(path).read()


def test_manifest_has_one_record_after_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    manifest = IngestionManifest(path)
    manifest.register(metadata())
    manifest.register(metadata())

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["manifest_version"] == 1
    assert len(payload["ingestions"]) == 1
