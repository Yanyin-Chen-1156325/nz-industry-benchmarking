"""Pure deterministic Phase 9 dependency planner."""

from __future__ import annotations

from nz_industry_benchmarking.gold.service import (
    calculate_gold_input_fingerprint_from_silver,
)
from nz_industry_benchmarking.incremental.models import (
    IncrementalPlan,
    LayerDecision,
    PipelineState,
)
from nz_industry_benchmarking.ingestion.models import IngestionMetadata
from nz_industry_benchmarking.silver.service import (
    calculate_input_fingerprint_from_identities,
)


def plan_incremental_processing(
    candidate: IngestionMetadata,
    state: PipelineState,
) -> IncrementalPlan:
    """Plan safe work from artifact and downstream fingerprint state."""
    identity = (candidate.ingestion_id, candidate.source_sha256)
    artifact_in_bronze = identity in state.bronze_identities
    artifact_status = (
        "ALREADY_PROCESSED" if artifact_in_bronze else "NEW_ARTIFACT"
    )
    overlap = 0 if artifact_in_bronze else state.overlapping_observations
    changed = 0 if artifact_in_bronze else state.changed_existing_observations

    if overlap:
        reason = (
            "Candidate overlaps existing Bronze observation identities; "
            "revision/version precedence is deferred to Phase 10."
        )
        deferred = LayerDecision("Bronze", "DEFERRED", reason, (), None)
        return IncrementalPlan(
            pipeline_status="DEFERRED_REVISION",
            artifact_status=artifact_status,
            source_file=candidate.source_file,
            source_sha256=candidate.source_sha256,
            dataset_year=candidate.dataset_year,
            dataset_version=candidate.dataset_version,
            overlap_observations=overlap,
            changed_existing_observations=changed,
            revision_sensitive=True,
            bronze=deferred,
            silver=LayerDecision("Silver", "DEFERRED", reason, (), None),
            gold=LayerDecision("Gold", "DEFERRED", reason, (), None),
        )

    expected_identities = set(state.bronze_identities)
    expected_identities.add(identity)
    silver_expected = calculate_input_fingerprint_from_identities(
        frozenset(expected_identities)
    )
    gold_expected = calculate_gold_input_fingerprint_from_silver(
        frozenset({silver_expected})
    )

    bronze_action = "CURRENT" if artifact_in_bronze else "REQUIRED"
    silver_current = state.silver_fingerprints == {silver_expected}
    silver_action = "CURRENT" if silver_current else "REQUIRED"
    gold_current = silver_current and state.gold_fingerprints == {gold_expected}
    gold_action = "CURRENT" if gold_current else "REQUIRED"
    pipeline_status = (
        "NO_OP"
        if {bronze_action, silver_action, gold_action} == {"CURRENT"}
        else "PROCESS_REQUIRED"
    )

    return IncrementalPlan(
        pipeline_status=pipeline_status,
        artifact_status=artifact_status,
        source_file=candidate.source_file,
        source_sha256=candidate.source_sha256,
        dataset_year=candidate.dataset_year,
        dataset_version=candidate.dataset_version,
        overlap_observations=0,
        changed_existing_observations=0,
        revision_sensitive=False,
        bronze=LayerDecision(
            "Bronze",
            bronze_action,
            (
                "Source SHA-256 already exists in Bronze."
                if artifact_in_bronze
                else "New non-overlapping source SHA-256 is eligible for Bronze."
            ),
            tuple(sorted(digest for _, digest in state.bronze_identities)),
            candidate.source_sha256,
        ),
        silver=LayerDecision(
            "Silver",
            silver_action,
            (
                "Silver fingerprint matches effective Bronze input."
                if silver_current
                else "Bronze input fingerprint differs from current Silver."
            ),
            tuple(sorted(state.silver_fingerprints)),
            silver_expected,
        ),
        gold=LayerDecision(
            "Gold",
            gold_action,
            (
                "Gold fingerprint matches effective Silver input."
                if gold_current
                else "Silver input requires a current Gold snapshot."
            ),
            tuple(sorted(state.gold_fingerprints)),
            gold_expected,
        ),
    )
