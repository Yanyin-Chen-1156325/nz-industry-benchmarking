"""Result model for one logical Silver processing attempt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SilverWriteResult:
    """Counts and identity for a Silver Delta snapshot."""

    table_path: str
    input_fingerprint: str
    bronze_input_rows: int
    silver_output_rows: int
    valid_rows: int
    invalid_rows: int
    status_counts: dict[str, int]
    duplicate: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible processing summary."""
        return asdict(self)
