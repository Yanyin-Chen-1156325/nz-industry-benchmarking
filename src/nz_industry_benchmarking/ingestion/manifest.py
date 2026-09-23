"""Local logical-ingestion registry with atomic manifest writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nz_industry_benchmarking.ingestion.errors import ManifestError
from nz_industry_benchmarking.ingestion.models import IngestionMetadata

MANIFEST_VERSION = 1


@dataclass(frozen=True, slots=True)
class Registration:
    """Manifest registration result."""

    metadata: IngestionMetadata
    inserted: bool


class IngestionManifest:
    """Persist one metadata record per unique source artifact hash."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def register(self, metadata: IngestionMetadata) -> Registration:
        """Insert metadata once, returning the original on duplicate attempts."""
        records = self.read()
        existing = next(
            (
                record
                for record in records
                if record.source_sha256 == metadata.source_sha256
            ),
            None,
        )
        if existing is not None:
            return Registration(metadata=existing, inserted=False)

        records.append(metadata)
        self._write(records)
        return Registration(metadata=metadata, inserted=True)

    def read(self) -> list[IngestionMetadata]:
        """Read and validate all metadata records from the manifest."""
        if not self.path.exists():
            return []
        if not self.path.is_file():
            raise ManifestError(f"Ingestion manifest is not a file: {self.path}")

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ManifestError(
                    f"Ingestion manifest root must be an object: {self.path}"
                )
            if payload.get("manifest_version") != MANIFEST_VERSION:
                raise ManifestError(
                    f"Unsupported ingestion manifest version: {self.path}"
                )
            raw_records = payload.get("ingestions")
            if not isinstance(raw_records, list):
                raise ManifestError(
                    f"Ingestion manifest has no records list: {self.path}"
                )
            return [IngestionMetadata.from_dict(record) for record in raw_records]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ManifestError(
                f"Ingestion manifest is invalid: {self.path}: {error}"
            ) from error

    def _write(self, records: list[IngestionMetadata]) -> None:
        """Atomically replace the manifest after writing a complete new copy."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "manifest_version": MANIFEST_VERSION,
            "ingestions": [record.to_dict() for record in records],
        }
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                json.dump(payload, temporary, indent=2, ensure_ascii=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise ManifestError(
                f"Could not write ingestion manifest {self.path}: {error}"
            ) from error
