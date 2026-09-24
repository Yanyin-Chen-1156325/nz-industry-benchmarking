"""Inspectable models for data-quality check and report results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QualityCheckResult:
    """Outcome of one stable quality rule."""

    rule_id: str
    dimension: str
    severity: str
    status: str
    description: str
    affected_rows: int | None
    details: str


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Complete result for one Silver quality assessment."""

    dataset_path: str
    generated_at: str
    overall_result: str
    rows_processed: int
    rows_accepted: int
    rows_rejected: int
    checks_executed: int
    passed_checks: int
    failed_checks: int
    validation_failure_counts: dict[str, int]
    checks: tuple[QualityCheckResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible report."""
        payload = asdict(self)
        payload["checks"] = list(payload["checks"])
        return payload
