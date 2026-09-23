# Architecture

## Implemented ingestion, Bronze, and Silver boundaries

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

The command emits structured JSON events for start, source load, successful
registration, duplicate detection, and failure. Runtime settings come from
environment variables, CLI arguments, or documented defaults.

## Not implemented

The broader Phase 6 quality framework, Gold processing, metric calculation,
APIs, Databricks jobs, and deployment workflows remain outside the implemented
architecture and require approval in their respective phases.
