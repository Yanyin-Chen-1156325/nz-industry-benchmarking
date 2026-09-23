"""Ingestion-specific exceptions with user-facing messages."""


class IngestionError(Exception):
    """Base class for expected ingestion failures."""


class SourceFileNotFoundError(IngestionError):
    """Raised when the configured source file cannot be found."""


class SourceCsvError(IngestionError):
    """Raised when the source cannot be read as the expected CSV structure."""


class SourceSchemaError(SourceCsvError):
    """Raised when the CSV header differs from the Phase 0 source contract."""


class ManifestError(IngestionError):
    """Raised when the ingestion manifest cannot be read or written safely."""
