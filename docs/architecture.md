# Architecture

## Implemented data-product boundaries

Phase 3 implements only the raw-file ingestion boundary:

```text
Configured Stats NZ AES CSV
             |
             v
  Raw string-preserving loader
             |
      +------+------+
      |             |
      v             v
  In-memory rows   SHA-256 identity
        |              |
        |              v
        |    Local ingestion manifest
        |
        v
Raw-string PySpark DataFrame
        |
        v
 Bronze Delta table
        |
        v
Typed and validated PySpark transformation
        |
        v
 Silver Delta table
        |
        v
 PySpark quality assessment
        |
        v
 Inspectable JSON quality report
        |
        v
 Approved M1-M7 PySpark transformations
        |
        v
 Gold metric Delta table
        |
        +------------------+
        |                  |
        v                  v
 Read-only M4-M6      Gold metric/trend
 benchmark queries        queries
        |                  |
        +--------+---------+
                 v
         Read-only REST API
                 |
                 v
       Minimal browser frontend
```

The loader verifies that the file exists and that its header matches the source
contract documented in [`dataset.md`](dataset.md). All row values remain source
strings; it does not perform type conversion, label standardization, protected
value interpretation, or business calculations.

The local manifest records metadata rather than source rows. Its logical key is
the exact source artifact SHA-256, so sequential attempts to ingest identical
bytes produce one manifest record. Manifest replacement is atomic within the
local filesystem.

Phase 4 consumes the Phase 3 `IngestionOutcome`; it does not reopen or reinterpret
the CSV inside the Bronze layer. PySpark creates an explicit schema containing the
10 source columns as non-null strings, followed by ingestion and row-lineage
metadata. The result is appended to the local Delta path configured by
`BRONZE_TABLE_PATH` (default `data/bronze/aes`).

Logical idempotency uses the source SHA-256 as `ingestion_id`. Before an append,
the writer checks for that identity and verifies its stored row count. Delta
transaction identifiers also protect a retried append. A complete existing
ingestion is reported as a duplicate with zero inserted rows; a partial or
conflicting ingestion fails instead of being silently accepted.

`source_row_number` is a one-based position in the source CSV data rows. It
preserves row-level lineage even if two raw rows contain identical values. The
Bronze data, Delta log, ingestion manifest, and source CSV are local generated
artifacts and are excluded from Git.

Phase 5 reads only the implemented Bronze Delta table. It validates the exact
Bronze column/type contract, converts the year and published numeric values to
logical types, classifies protected and unusable values, and validates source
metadata and observation identity. It does not reopen the CSV.

Every Bronze row produces one Silver row. Invalid or unavailable records remain
in `data/silver/aes_observations` with stable `record_id`, validation rule IDs,
failure reasons, and Bronze lineage. No invalid row is silently filtered.

The sorted set of Bronze ingestion identities produces a deterministic Silver
input fingerprint. The Silver table is a complete snapshot: a new fingerprint
overwrites the prior logical snapshot, while the same fingerprint is verified
and skipped. Delta transaction identity provides retry protection.

Phase 6 reads the persisted Silver Delta table as its primary assessment
boundary. Reusable PySpark conditions evaluate schema, completeness, validity,
uniqueness, and source/data-contract consistency without modifying Silver. The
framework emits 16 stable check outcomes and an overall PASS/FAIL result. Any
failed blocking rule makes the result FAIL; informational rules count legitimate
confidential, suppressed, and negative published observations without failing
the dataset.

The JSON report is replaced atomically at
`data/quality/silver-quality-report.json` by default. It records processed,
accepted, and rejected row counts, each check result and affected-row count, and
the Phase 5 validation-rule failure distribution. Invalid source records remain
in Silver with their original rule IDs, reasons, and lineage; the quality layer
does not discard or rewrite them.

The command emits structured JSON events for start, source load, successful
registration, duplicate detection, and failure. Runtime settings come from
environment variables, CLI arguments, or documented defaults.

Phase 7 reads only the Silver Delta snapshot and produces one long-format Gold
table at `data/gold/industry_financial_metrics`. A distinct Silver
year/aggregation/industry scaffold ensures absent H01, H23, or H40 observations
become explicit unavailable metric rows rather than disappearing. Direct M1-M3
rows and derived M4-M6 rows share one analytical grain; M7 is represented by
the `metric_status` and component-status fields on every metric row.

Year-over-year joins include year, aggregation level, and industry code, and
require exactly `current.year - 1`. They never bridge a missing year. Gold
retains current/prior Silver record IDs and source artifact identities for
lineage. The input fingerprint combines the Silver snapshot identity with the
Gold schema and logic versions. An identical rerun verifies and skips the
existing snapshot; a new fingerprint replaces the complete snapshot.

Phase 8 reads the Gold Delta table as its only analytical input. It does not
recalculate metrics or persist a second analytical table. A bounded query first
selects one year, one M4-M6 metric, and one NZSIOC aggregation level, then ranks
only `PUBLISHED` values. The same reusable transformation can rank all partitions
independently for batch verification.

Top increases retain positive values and order signed values descending. Top
decreases retain negative values and order signed values ascending. Largest
movements includes positive, negative, and zero values and orders their absolute
magnitude descending while returning the original signed value. Window
partitions are `(year, metric_id, industry_aggregation_nzsioc)`, so years,
metrics, levels, and units cannot mix.

After the concept-specific primary order, ties use
`industry_code_nzsioc ASC`, `industry_name_nzsioc ASC`, and
`metric_record_id ASC`. The resulting `rank_position` is deterministic and
unique within its partition. Gold record and lineage identifiers flow through
unchanged for traceability. Because rankings are inexpensive bounded views over
the small Gold table, no benchmark Delta table is materialized.

Phase 9 composes the existing services behind a deterministic planner. Source
artifact identity remains its byte-level SHA-256, not its filename. The planner
derives the expected Silver fingerprint from the sorted set of Bronze
`(ingestion_id, source_sha256)` identities, then derives the expected Gold
fingerprint from the Silver identity and Gold contract versions.

An artifact already present in Bronze is `CURRENT`. If Silver and Gold hold the
expected singleton fingerprints, the entire run is `NO_OP` and no writer is
called. A safe new, non-overlapping artifact makes Bronze, Silver, and Gold
`REQUIRED`; Bronze appends once and the current snapshot writers rebuild Silver
and Gold. Benchmark queries remain stateless.

The safe automatic boundary is deliberately narrower than revision handling.
Any candidate observation grain overlapping Bronze is `DEFERRED_REVISION`
before a Bronze write. The report distinguishes overlapping observations from
ones whose ten raw fields changed, but it does not select an authoritative
release. See [`incremental-processing.md`](incremental-processing.md).

Phase 10 consumes that deferred state. An incoming official release may take
precedence only when its configured `dataset_year` is strictly greater than the
current release year for every overlap. Equal-year artifacts are ambiguous;
version strings, filenames, checksums, and processing timestamps are never used
as ordering signals.

Eligible releases append their complete raw artifact to Bronze, preserving a
history grain of `(ingestion_id, source_row_number)`. Silver first selects the
greatest unambiguous release year separately at the approved observation grain,
then applies the existing parsing and validation. Observations absent from the
new release stay sourced from the older release. Gold sees the new Silver
fingerprint and rebuilds without any metric-rule changes.

Each incoming artifact has one atomic JSON revision report containing release
lineage, classification counts, value-status transitions, current-view impact,
and rebuild decisions. The report and Bronze history provide previous-version
traceability while Silver remains a unique analytical current view. See
[`revision-handling.md`](revision-handling.md).

Phase 12 is a thin delivery boundary over Gold and the Phase 8 benchmark service.
FastAPI routes validate supported years, industry identifiers, metric IDs,
aggregation levels, ranking types, and top-N bounds, then call an application
service. The service depends on an `AnalyticsRepository` protocol rather than
Spark directly. This keeps HTTP contract tests lightweight and makes deployment
changes possible without rewriting routes.

The production adapter owns no business calculations. It selects existing Gold
rows for industry, performance, and chronological trend responses, and delegates
ranking to `query_benchmarks`. A single Spark session is created during the API
application lifespan and shared by requests. No relational database or duplicate
API data store is introduced.

Responses expose approved metric names, values, statuses, units, dimensions, and
compact lineage. The mapping explicitly forces every non-published numeric value
to null. Expected no-data, invalid-request, storage-unavailable, and unexpected
failure paths have stable public error envelopes; raw Spark/Delta details remain
server-side. See [`api.md`](api.md).

Phase 13 is a static browser client of the REST API. A small API client maps only
consumer-facing fields into presentation objects; formatting/status functions
and DOM rendering remain separate. The UI requests industries, performance,
chronological trends, and Phase 8 rankings over HTTP. It does not import pipeline
code, access Delta, run Spark, calculate metrics, or rank rows.

The API uses an explicit configurable CORS allowlist for the independently served
local frontend. No wildcard origin, frontend framework, chart dependency, or
state-management package is introduced. See [`frontend.md`](frontend.md).

## Not implemented

Authentication, Databricks jobs, deployment, and CI/CD workflows remain outside
the implemented architecture and require approval in their respective phases.
