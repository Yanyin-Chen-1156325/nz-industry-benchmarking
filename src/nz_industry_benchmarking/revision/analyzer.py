"""Classify an incoming release against the deterministic current Bronze view."""

from __future__ import annotations

import hashlib

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from nz_industry_benchmarking.ingestion.models import (
    EXPECTED_COLUMNS,
    IngestionMetadata,
)
from nz_industry_benchmarking.revision.models import RevisionReport
from nz_industry_benchmarking.silver.current_view import (
    OBSERVATION_KEY,
    select_current_bronze_view,
)

PRECEDENCE_RULE = (
    "For an overlapping observation, incoming dataset_year must be strictly "
    "greater than the selected release dataset_year; dataset_version strings, "
    "filenames, and SHA-256 values are not ordered."
)
METADATA_COLUMNS = (
    "Industry_name_NZSIOC",
    "Units",
    "Variable_name",
    "Variable_category",
    "Industry_code_ANZSIC06",
)


def analyze_revision(
    candidate: DataFrame,
    bronze_history_without_candidate: DataFrame,
    metadata: IngestionMetadata,
) -> RevisionReport:
    """Return mutually inspectable revision counts and precedence decision."""
    current = select_current_bronze_view(bronze_history_without_candidate)
    incoming = candidate.select(*EXPECTED_COLUMNS).distinct()
    current_rows = current.select(
        *EXPECTED_COLUMNS,
        "ingestion_id",
        "source_file",
        "source_url",
        "source_sha256",
        "dataset_year",
        "dataset_version",
        "ingestion_timestamp",
    )

    incoming_keys = incoming.select(*OBSERVATION_KEY).distinct()
    current_keys = current_rows.select(*OBSERVATION_KEY).distinct()
    overlap_keys = incoming_keys.join(current_keys, list(OBSERVATION_KEY), "inner")
    overlap_count = overlap_keys.count()
    new_count = incoming_keys.join(
        current_keys, list(OBSERVATION_KEY), "left_anti"
    ).count()
    absent_count = current_keys.join(
        incoming_keys, list(OBSERVATION_KEY), "left_anti"
    ).count()

    compared = incoming.alias("new").join(
        current_rows.alias("old"), list(OBSERVATION_KEY), "inner"
    )
    value_changed = F.col("new.Value") != F.col("old.Value")
    metadata_changed = _any_changed("new", "old", METADATA_COLUMNS)
    counts = compared.agg(
        F.sum(F.when(~value_changed & ~metadata_changed, 1).otherwise(0)).alias(
            "unchanged"
        ),
        F.sum(F.when(value_changed, 1).otherwise(0)).alias("revised_values"),
        F.sum(F.when(metadata_changed, 1).otherwise(0)).alias("revised_metadata"),
        F.sum(F.when(value_changed | metadata_changed, 1).otherwise(0)).alias(
            "changed_overlap"
        ),
    ).first()
    transitions = {
        row.transition: int(row["count"])
        for row in compared.where(value_changed)
        .select(
            F.concat(
                _value_status("old.Value"),
                F.lit("->"),
                _value_status("new.Value"),
            ).alias("transition")
        )
        .groupBy("transition")
        .count()
        .collect()
    }
    previous_releases = tuple(
        sorted(
            (
                {
                    "release_identity": _release_identity(
                        row.dataset_year,
                        row.dataset_version,
                        row.source_sha256,
                    ),
                    "dataset_year": row.dataset_year,
                    "dataset_version": row.dataset_version,
                    "source_sha256": row.source_sha256,
                    "source_file": row.source_file,
                    "source_url": row.source_url,
                    "ingestion_timestamp": str(row.ingestion_timestamp),
                }
                for row in compared.select(
                    "old.dataset_year",
                    "old.dataset_version",
                    "old.source_sha256",
                    "old.source_file",
                    "old.source_url",
                    "old.ingestion_timestamp",
                )
                .distinct()
                .collect()
            ),
            key=lambda release: (
                release["dataset_year"],
                release["source_sha256"],
            ),
        )
    )
    previous_years = {int(item["dataset_year"]) for item in previous_releases}
    precedence_safe = bool(overlap_count) and all(
        metadata.dataset_year > year for year in previous_years
    )
    overall_result = "ELIGIBLE" if precedence_safe else "DEFERRED_AMBIGUOUS"
    message = (
        "Incoming official release has a strictly greater dataset_year for every "
        "overlapping current observation."
        if precedence_safe
        else (
            "Release precedence is insufficient or this is not an overlapping "
            "revision."
        )
    )
    previous_hashes = sorted(
        str(release["source_sha256"]) for release in previous_releases
    )
    revision_id = hashlib.sha256(
        "\n".join(["aes-revision-v1", *previous_hashes, metadata.source_sha256]).encode(
            "utf-8"
        )
    ).hexdigest().upper()
    incoming_release = {
        "release_identity": _release_identity(
            metadata.dataset_year,
            metadata.dataset_version,
            metadata.source_sha256,
        ),
        **metadata.to_dict(),
    }
    unchanged = int(counts.unchanged or 0)
    revised_values = int(counts.revised_values or 0)
    revised_metadata = int(counts.revised_metadata or 0)
    changed_overlap = int(counts.changed_overlap or 0)
    return RevisionReport(
        revision_id=revision_id,
        overall_result=overall_result,
        precedence_rule=PRECEDENCE_RULE,
        previous_releases=previous_releases,
        incoming_release=incoming_release,
        overlapping_observations=overlap_count,
        unchanged_republications=unchanged,
        revised_values=revised_values,
        revised_metadata=revised_metadata,
        newly_added_observations=new_count,
        observations_absent_from_incoming=absent_count,
        current_view_observations_changed=changed_overlap + new_count,
        value_transition_counts=dict(sorted(transitions.items())),
        silver_rebuild_required=precedence_safe,
        gold_rebuild_required=precedence_safe,
        message=message,
    )


def _any_changed(new_alias: str, old_alias: str, columns: tuple[str, ...]):
    result = F.lit(False)
    for column in columns:
        result = result | ~F.col(f"{new_alias}.{column}").eqNullSafe(
            F.col(f"{old_alias}.{column}")
        )
    return result


def _value_status(column: str):
    value = F.col(column)
    return (
        F.when(value == "C", F.lit("CONFIDENTIAL"))
        .when(value == "S", F.lit("SUPPRESSED"))
        .when(
            value.rlike(r"^[+-]?(?:\d+(?:,\d{3})*|\d*)(?:\.\d+)?$"),
            F.lit("PUBLISHED"),
        )
        .otherwise(F.lit("OTHER"))
    )


def _release_identity(dataset_year: int, dataset_version: str, digest: str) -> str:
    return f"{dataset_year}|{dataset_version}|{digest}"
