"""Result models returned by Bronze persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BronzeWriteResult:
    """Summary of one idempotent Bronze write attempt."""

    table_path: str
    ingestion_id: str
    source_sha256: str
    input_rows: int
    inserted_rows: int
    total_rows: int
    duplicate: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible write summary."""
        return asdict(self)
