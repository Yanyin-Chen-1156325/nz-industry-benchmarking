"""Deterministic decision tests for Phase 9 incremental processing."""

from __future__ import annotations

from dataclasses import replace

from nz_industry_benchmarking.gold.service import (
    calculate_gold_input_fingerprint_from_silver,
)
from nz_industry_benchmarking.incremental.models import PipelineState
from nz_industry_benchmarking.incremental.planner import plan_incremental_processing
from nz_industry_benchmarking.ingestion.models import IngestionMetadata
from nz_industry_benchmarking.silver.service import (
    calculate_input_fingerprint_from_identities,
)


def _candidate(**overrides: object) -> IngestionMetadata:
    values = {
        "ingestion_id": "A" * 64,
        "source_file": "data/raw/aes.csv",
        "source_url": "https://www.stats.govt.nz/aes.csv",
        "source_sha256": "A" * 64,
        "dataset_year": 2025,
        "dataset_version": "2025-provisional",
        "ingestion_timestamp": "2026-09-24T01:02:03Z",
        "row_count": 3,
        "schema_version": "aes-public-csv-v1",
    }
    values.update(overrides)
    return IngestionMetadata(**values)


def _current_state(candidate: IngestionMetadata) -> PipelineState:
    identities = frozenset({(candidate.ingestion_id, candidate.source_sha256)})
    silver = calculate_input_fingerprint_from_identities(identities)
    gold = calculate_gold_input_fingerprint_from_silver(frozenset({silver}))
    return PipelineState(identities, frozenset({silver}), frozenset({gold}))


def test_exact_artifact_rerun_is_a_complete_no_op() -> None:
    candidate = _candidate()
    plan = plan_incremental_processing(candidate, _current_state(candidate))

    assert plan.pipeline_status == "NO_OP"
    assert plan.artifact_status == "ALREADY_PROCESSED"
    assert (plan.bronze.action, plan.silver.action, plan.gold.action) == (
        "CURRENT",
        "CURRENT",
        "CURRENT",
    )


def test_same_filename_with_different_hash_is_a_new_artifact() -> None:
    old = _candidate()
    new = replace(old, ingestion_id="B" * 64, source_sha256="B" * 64)
    state = _current_state(old)

    plan = plan_incremental_processing(new, state)

    assert plan.source_file == old.source_file
    assert plan.artifact_status == "NEW_ARTIFACT"
    assert plan.bronze.action == "REQUIRED"
    assert plan.silver.action == "REQUIRED"
    assert plan.gold.action == "REQUIRED"


def test_genuinely_new_non_overlapping_artifact_is_eligible() -> None:
    plan = plan_incremental_processing(_candidate(), PipelineState(
        frozenset(), frozenset(), frozenset()
    ))

    assert plan.pipeline_status == "PROCESS_REQUIRED"
    assert plan.revision_sensitive is False
    assert plan.bronze.reason.startswith("New non-overlapping")


def test_silver_is_stale_when_bronze_identity_changes() -> None:
    old = _candidate()
    new = replace(old, ingestion_id="B" * 64, source_sha256="B" * 64)
    plan = plan_incremental_processing(new, _current_state(old))

    assert plan.silver.action == "REQUIRED"
    assert plan.silver.current_fingerprints
    assert plan.silver.expected_fingerprint not in plan.silver.current_fingerprints


def test_gold_is_stale_when_silver_fingerprint_changes() -> None:
    candidate = _candidate()
    identities = frozenset({(candidate.ingestion_id, candidate.source_sha256)})
    silver = calculate_input_fingerprint_from_identities(identities)
    state = PipelineState(identities, frozenset({silver}), frozenset({"STALE"}))

    plan = plan_incremental_processing(candidate, state)

    assert plan.silver.action == "CURRENT"
    assert plan.gold.action == "REQUIRED"


def test_revision_sensitive_overlap_is_deferred_to_phase_10() -> None:
    candidate = _candidate()
    state = PipelineState(
        frozenset({("OLD", "OLD")}),
        frozenset(),
        frozenset(),
        overlapping_observations=2,
        changed_existing_observations=1,
    )

    plan = plan_incremental_processing(candidate, state)

    assert plan.pipeline_status == "DEFERRED_REVISION"
    assert plan.revision_sensitive is True
    assert plan.changed_existing_observations == 1
    assert {plan.bronze.action, plan.silver.action, plan.gold.action} == {"DEFERRED"}


def test_repeated_planning_is_deterministic() -> None:
    candidate = _candidate()
    state = _current_state(candidate)

    assert plan_incremental_processing(candidate, state) == plan_incremental_processing(
        candidate, state
    )
