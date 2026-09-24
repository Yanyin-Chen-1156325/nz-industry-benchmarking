"""Inspect persisted Delta identities without changing pipeline state."""

from __future__ import annotations

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.schema import build_bronze_dataframe
from nz_industry_benchmarking.incremental.config import IncrementalConfig
from nz_industry_benchmarking.incremental.errors import IncrementalStateError
from nz_industry_benchmarking.incremental.models import PipelineState
from nz_industry_benchmarking.ingestion.models import (
    EXPECTED_COLUMNS,
    IngestionOutcome,
)

OBSERVATION_KEY = (
    "Year",
    "Industry_aggregation_NZSIOC",
    "Industry_code_NZSIOC",
    "Variable_code",
)


def inspect_pipeline_state(
    spark: SparkSession,
    outcome: IngestionOutcome,
    config: IncrementalConfig,
) -> PipelineState:
    """Read artifact, overlap, and snapshot fingerprints for planning."""
    bronze = _read_delta(spark, config.bronze.table_path)
    if bronze is None:
        identities: frozenset[tuple[str, str]] = frozenset()
    else:
        _require_columns(bronze, {"ingestion_id", "source_sha256", *EXPECTED_COLUMNS})
        identities = frozenset(
            (row.ingestion_id, row.source_sha256)
            for row in bronze.select("ingestion_id", "source_sha256")
            .distinct()
            .collect()
        )

    candidate_identity = (
        outcome.metadata.ingestion_id,
        outcome.metadata.source_sha256,
    )
    overlap = 0
    changed = 0
    if bronze is not None and candidate_identity not in identities:
        candidate = build_bronze_dataframe(spark, outcome)
        overlap, changed = _compare_observations(candidate, bronze)

    silver_fingerprints = _read_fingerprints(
        spark,
        config.silver.silver_path,
        "silver_input_fingerprint",
    )
    gold_fingerprints = _read_fingerprints(
        spark,
        config.gold.gold_metrics_path,
        "gold_input_fingerprint",
    )
    return PipelineState(
        bronze_identities=identities,
        silver_fingerprints=silver_fingerprints,
        gold_fingerprints=gold_fingerprints,
        overlapping_observations=overlap,
        changed_existing_observations=changed,
    )


def _compare_observations(candidate: DataFrame, bronze: DataFrame) -> tuple[int, int]:
    candidate_rows = candidate.select(*EXPECTED_COLUMNS).distinct()
    existing_rows = bronze.select(*EXPECTED_COLUMNS).distinct()
    candidate_keys = candidate_rows.select(*OBSERVATION_KEY).distinct()
    existing_keys = existing_rows.select(*OBSERVATION_KEY).distinct()
    overlap_keys = candidate_keys.join(existing_keys, list(OBSERVATION_KEY), "inner")
    overlap = overlap_keys.count()
    if overlap == 0:
        return 0, 0

    candidate_digests = _with_row_digest(candidate_rows)
    existing_digests = _with_row_digest(existing_rows)
    exact_keys = (
        candidate_digests.join(
            existing_digests,
            [*OBSERVATION_KEY, "_row_digest"],
            "inner",
        )
        .select(*OBSERVATION_KEY)
        .distinct()
    )
    changed = overlap_keys.join(exact_keys, list(OBSERVATION_KEY), "left_anti").count()
    return overlap, changed


def _with_row_digest(dataframe: DataFrame) -> DataFrame:
    values = [F.coalesce(F.col(column), F.lit("<null>")) for column in EXPECTED_COLUMNS]
    return dataframe.select(
        *OBSERVATION_KEY,
        F.sha2(F.concat_ws("\u001f", *values), 256).alias("_row_digest"),
    ).distinct()


def _read_delta(spark: SparkSession, path) -> DataFrame | None:
    uri = path.resolve().as_uri()
    if not DeltaTable.isDeltaTable(spark, uri):
        return None
    return spark.read.format("delta").load(uri)


def _read_fingerprints(
    spark: SparkSession,
    path,
    column: str,
) -> frozenset[str]:
    dataframe = _read_delta(spark, path)
    if dataframe is None:
        return frozenset()
    _require_columns(dataframe, {column})
    return frozenset(
        str(row[column]) for row in dataframe.select(column).distinct().collect()
    )


def _require_columns(dataframe: DataFrame, required: set[str]) -> None:
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise IncrementalStateError(
            f"Persisted pipeline state is missing required columns: {missing!r}."
        )
