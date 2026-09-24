"""Small inspectable revision audit and execution models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from nz_industry_benchmarking.bronze.models import BronzeWriteResult
from nz_industry_benchmarking.gold.models import GoldWriteResult
from nz_industry_benchmarking.silver.models import SilverWriteResult


@dataclass(frozen=True, slots=True)
class RevisionReport:
    revision_id: str
    overall_result: str
    precedence_rule: str
    previous_releases: tuple[dict[str, Any], ...]
    incoming_release: dict[str, Any]
    overlapping_observations: int
    unchanged_republications: int
    revised_values: int
    revised_metadata: int
    newly_added_observations: int
    observations_absent_from_incoming: int
    current_view_observations_changed: int
    value_transition_counts: dict[str, int]
    silver_rebuild_required: bool
    gold_rebuild_required: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RevisionReport:
        return cls(
            revision_id=str(value["revision_id"]),
            overall_result=str(value["overall_result"]),
            precedence_rule=str(value["precedence_rule"]),
            previous_releases=tuple(value["previous_releases"]),
            incoming_release=dict(value["incoming_release"]),
            overlapping_observations=int(value["overlapping_observations"]),
            unchanged_republications=int(value["unchanged_republications"]),
            revised_values=int(value["revised_values"]),
            revised_metadata=int(value["revised_metadata"]),
            newly_added_observations=int(value["newly_added_observations"]),
            observations_absent_from_incoming=int(
                value["observations_absent_from_incoming"]
            ),
            current_view_observations_changed=int(
                value["current_view_observations_changed"]
            ),
            value_transition_counts={
                str(key): int(count)
                for key, count in value["value_transition_counts"].items()
            },
            silver_rebuild_required=bool(value["silver_rebuild_required"]),
            gold_rebuild_required=bool(value["gold_rebuild_required"]),
            message=str(value["message"]),
        )


@dataclass(frozen=True, slots=True)
class RevisionRunResult:
    report: RevisionReport
    duplicate: bool
    bronze_result: BronzeWriteResult | None = None
    silver_result: SilverWriteResult | None = None
    gold_result: GoldWriteResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
