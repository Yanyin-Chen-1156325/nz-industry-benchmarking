# Incremental processing operations

Phase 9 adds a small dependency-aware planner around the existing ingestion,
Bronze, Silver, and Gold services. It does not introduce a scheduler or change
the persisted schemas.

Run it from the repository root:

```powershell
python -m nz_industry_benchmarking.incremental
```

The command reads the configured AES source, calculates its exact byte-level
SHA-256, registers the artifact in the ingestion manifest, inspects existing
Delta state, and prints an inspectable JSON decision and execution result.

## Decisions

The source filename is descriptive only. Artifact identity is the SHA-256, also
used as `ingestion_id`. Dataset year, version, URL, original path, and checksum
continue through the existing lineage fields.

Each layer receives one action:

- `CURRENT`: the source identity or effective input fingerprint already matches;
- `REQUIRED`: the layer is absent or its effective input fingerprint changed;
- `DEFERRED`: processing would require Phase 10 revision precedence semantics.

The overall result is `NO_OP`, `PROCESS_REQUIRED`, or `DEFERRED_REVISION`.
Bronze additions make Silver stale; a new Silver fingerprint makes Gold stale.
Benchmarking remains a read-only Gold query and has no incremental state.

For a fully current source, no Bronze, Silver, or Gold write function is called.
Use the actual-data check to prove this behavior:

```powershell
python scripts/verify_incremental.py
```

## Safe automatic scope

Phase 9 automatically processes a new artifact only when its observed source
grain does not overlap Bronze:

```text
Year
+ Industry_aggregation_NZSIOC
+ Industry_code_NZSIOC
+ Variable_code
```

This supports additive files such as a new year delivered without previously
loaded observations. Bronze appends the new artifact once; Silver and Gold then
replace their deterministic complete snapshots using their existing writers.

If any candidate key already exists in Bronze, processing is deferred before a
Bronze write. The result reports total overlapping keys and how many do not have
an exact match across all ten raw source fields. Exact overlaps are also deferred
because appending them would duplicate observations and choosing one release is
a Phase 10 concern.

The ingestion manifest may therefore contain a discovered artifact that is not
yet present in Bronze. This is intentional: registration records discovery;
Bronze presence records successful data processing. A later run remains
deterministic and continues to report the same deferred decision.

## Phase 10 boundary

Phase 9 does not decide which overlapping release is authoritative, merge a
revised historical value, overwrite an observation by year, define release
ordering, or create SCD records. The AES 2025 file is provisional and contains
no row-level revision marker, so those rules require explicit Phase 10 approval.
Delta `MERGE` is therefore not appropriate in this phase: Bronze uses its
existing artifact-idempotent append, while Silver and Gold retain their existing
complete deterministic snapshot semantics.
