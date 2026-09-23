# Data dictionary

The inspected source columns and published variables are documented in
[`dataset.md`](dataset.md). Approved MVP metric definitions are documented in
[`business-rules.md`](business-rules.md).

## Bronze Delta table

Default location: `data/bronze/aes`

All 10 source columns are copied unchanged and stored as non-null Spark strings.
In particular, `Value` is not parsed, so numeric-looking text and the source `C`
and `S` markers remain exactly as supplied.

| Column | Spark type | Origin and meaning |
|---|---|---|
| `Year` | string | Raw AES source field. |
| `Industry_aggregation_NZSIOC` | string | Raw AES source field. |
| `Industry_code_NZSIOC` | string | Raw AES source field. |
| `Industry_name_NZSIOC` | string | Raw AES source field. |
| `Units` | string | Raw AES source field. |
| `Variable_code` | string | Raw AES source field. |
| `Variable_name` | string | Raw AES source field. |
| `Variable_category` | string | Raw AES source field. |
| `Value` | string | Raw AES value, including unchanged `C` and `S` markers. |
| `Industry_code_ANZSIC06` | string | Raw AES source field. |
| `ingestion_id` | string | Logical ingestion key; equal to the uppercase source SHA-256. |
| `source_file` | string | Source path captured by Phase 3. |
| `source_url` | string | Official source URL configured for ingestion. |
| `source_sha256` | string | SHA-256 of the exact source-file bytes. |
| `dataset_year` | integer | Dataset release year configured for ingestion. |
| `dataset_version` | string | Dataset release/version label. |
| `ingestion_timestamp` | timestamp | First logical ingestion time, stored in UTC. |
| `row_count` | long | Source data-row count repeated for traceability. |
| `schema_version` | string | Version of the enforced source contract. |
| `source_row_number` | long | One-based position among source data rows. |

The metadata fields are non-null. They describe source lineage only and are not
business measures.
