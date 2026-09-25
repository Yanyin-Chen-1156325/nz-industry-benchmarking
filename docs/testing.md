# Automated testing strategy and inventory

Phase 11 reviewed the tests accumulated during Phases 2-10 before adding any
coverage. The suite intentionally uses pytest, small synthetic fixtures, one
session-scoped local Spark session, and isolated `tmp_path` Delta locations. It
does not process the 60,255-row official AES file during normal pytest runs.

## Test layers

- Unit tests exercise pure configuration, ingestion, transformation, metric,
  ranking, fingerprint, incremental-planning, and revision-classification logic.
- Data-quality/contract tests assert Silver validation, DQ severity and report
  semantics, Gold grain/status invariants, and lineage requirements.
- Integration tests cross filesystem or Delta boundaries: manifest registration,
  Bronze/Silver/Gold persistence, quality reports, benchmark queries, incremental
  orchestration, and revision history/current-view behavior.

The Phase 9 incremental and Phase 10 revision integration tests together are the
implemented end-to-end smoke coverage. They start with synthetic CSV files and
cross ingestion, Bronze, Silver, and Gold. They also prove no-op Delta versions,
protected states, revision audit, and lineage. A third smoke test would duplicate
that expensive path without covering a new risk.

## Coverage inventory

| Component or behavior | Existing proof | Assessment |
|---|---|---|
| Foundation and configuration | Python/package tests plus composed environment propagation | Sufficient |
| Source loading | Raw strings, missing file, unexpected header, malformed row shape | Sufficient |
| Artifact identity/idempotency | SHA-256 manifest, duplicate registration, same filename/new hash | Sufficient |
| Bronze Delta | Raw `C`/`S` fidelity, metadata, duplicate no-op, conflicting logical ingestion | Sufficient |
| Silver transformation | Numeric/negative, C/S, unavailable/invalid, contextual labels | Sufficient |
| Silver validation/grain | Duplicate retention, metadata contract, aggregation-level identity | Sufficient |
| Data Quality | PASS/FAIL, blocking duplicates/schema/value, informational C/S/negative | Sufficient |
| Gold M1-M7 | Every Phase 1 example, protected inputs, negatives, gaps, level separation | Sufficient |
| YoY edge behavior | Missing prior year, zero/negative M4 base, unavailable inputs | Sufficient |
| Benchmarking | Three orderings, signs, eligibility, partitions, ties, empty/top-N | Sufficient |
| Incremental processing | Current/stale/no-op, additive artifact, revision deferral, Delta versions | Sufficient |
| Revision handling | Precedence ambiguity, all classifications, protected transitions, current view | Sufficient |
| Lineage | Bronze metadata, Gold arrays, revision old/new SHA continuity | Sufficient |
| Deterministic reruns | Manifest, every Delta layer, planner, ranking ties, revision audit | Sufficient |
| Operational failures | Missing/malformed source, schema failures, corrupt manifest, conflicting Bronze | Appropriate MVP coverage |
| REST API | Spark-free route contracts plus one temporary-Gold adapter integration | Sufficient for Phase 12 |

## Phase 11 gaps closed

Only four meaningful gaps were changed:

1. A composed configuration test now proves one supplied environment mapping
   reaches ingestion, Bronze, Silver, Gold, Spark, and revision-report settings.
2. The loader now has an explicit malformed row-shape test in addition to its
   missing-file and wrong-header tests.
3. The existing Bronze integration test now proves a partial/conflicting logical
   ingestion fails without appending rows.
4. Existing revision tests now assert equal-year current-view ambiguity raises,
   and that the selected incoming SHA continues from Silver into Gold while the
   previous SHA remains in the revision audit/Bronze history.

No new production behavior or business rule was introduced.

Phase 12 adds 12 Spark-free HTTP cases covering health/OpenAPI, industries,
performance, chronological trends, protected-value serialization, benchmark
delegation, parameter validation, no-data behavior, and safe 500/503 mappings.
One integration case crosses FastAPI, the real Spark repository, temporary Gold
Delta, and the existing Phase 8 benchmark service. It uses five synthetic Bronze
rows and does not read the official AES artifact.

Phase 13 adds two backend unit cases for the explicit configurable CORS allowlist.
Five dependency-free Node tests cover API response mapping, removal of
backend-only fields, protected/unavailable rendering, signed ranking values,
no-data mapping, and safe API-unavailable errors. The static frontend also uses
`node --check` for every JavaScript module and a deterministic copy-only build.

## Isolation and determinism

- All mutable source, manifest, report, and Delta paths use per-test temporary
  directories.
- Tests do not read existing local Bronze/Silver/Gold state or depend on order.
- Business timestamps are fixed in fixtures where output equality matters.
- Artifact IDs and fingerprints derive from deterministic fixture bytes or
  explicit test values.
- Spark is shared only as a process resource; persisted state is never shared.
- Idempotency tests rerun the same operation and inspect row counts, fingerprints,
  report equality, or Delta versions.

## CI test selection

Phase 14 partitions the suite into complementary fast and Spark/Delta runs.
During collection, any test that directly or transitively depends on the shared
`spark` fixture receives the registered `spark` marker. This keeps classification
tied to the actual runtime dependency and avoids changing test behavior or
repeating expensive cases.

Run the same selections locally with:

```powershell
python -m pytest -m "not spark"
python -m pytest -m spark
```

See [continuous integration](ci.md) for runner versions and workflow details.

## Intentional limitations

- Filesystem permission-denied behavior is platform-specific; deterministic
  missing-file, malformed-CSV, and schema errors cover the portable source
  contract.
- The suite does not load-test Spark, simulate concurrent writers, or test remote
  object-store failure/recovery.
- Most CLIs are thin adapters over directly tested services. Only the important
  ingestion missing-source exit contract has a dedicated CLI test.
- The official AES artifact is checked by explicit verification scripts, not the
  normal suite, keeping tests fast, isolated, and independent of ignored data.
- No coverage-percentage dependency was added; risk/behavior mapping is used
  instead of pursuing a numeric target.
