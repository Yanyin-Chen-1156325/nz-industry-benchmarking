"""Inspectable planning and execution results for Phase 9."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.silver.models import SilverWriteResult


@dataclass(frozen=True, slots=True)
class LayerDecision:
    """Current, required, or deferred status for one persisted layer."""

    layer: str
    action: str
    reason: str
    current_fingerprints: tuple[str, ...]
    expected_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class PipelineState:
    """Minimal persisted state needed for a deterministic plan."""

    bronze_identities: frozenset[tuple[str, str]]
    silver_fingerprints: frozenset[str]
    gold_fingerprints: frozenset[str]
    overlapping_observations: int = 0
    changed_existing_observations: int = 0


@dataclass(frozen=True, slots=True)
class IncrementalPlan:
    """Deterministic decision for one candidate source artifact."""

    pipeline_status: str
    artifact_status: str
    source_file: str
    source_sha256: str
    dataset_year: int
    dataset_version: str
    overlap_observations: int
    changed_existing_observations: int
    revision_sensitive: bool
    bronze: LayerDecision
    silver: LayerDecision
    gold: LayerDecision

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible planning evidence."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IncrementalRunResult:
    """Initial decision, executed actions, and verified final state."""

    initial_plan: IncrementalPlan
    final_plan: IncrementalPlan
    bronze_result: BronzeWriteResult | None = None
    silver_result: SilverWriteResult | None = None
    gold_result: GoldWriteResult | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a complete inspectable execution result."""
        return asdict(self)
