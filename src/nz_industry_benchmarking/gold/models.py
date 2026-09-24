"""Result model for a logical Gold processing attempt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldWriteResult:
    """Counts and identity for the Gold metric Delta snapshot."""

    table_path: str
    input_fingerprint: str
    silver_input_rows: int
    gold_output_rows: int
    metric_counts: dict[str, int]
    status_counts: dict[str, int]
    duplicate: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible processing summary."""
        return asdict(self)
