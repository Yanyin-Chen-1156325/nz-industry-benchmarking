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

## Silver Delta table

Default location: `data/silver/aes_observations`

Silver contains exactly one row for every Bronze row, including invalid or
unavailable records. Published labels are retained rather than standardized to
an invented meaning. In particular, both valid H04 and H06 labels and both H18
capitalization variants remain distinct.

| Column | Spark type | Meaning |
|---|---|---|
| `record_id` | string | Stable `ingestion_id:source_row_number` identifier. |
| `year` | integer | Parsed four-digit source year; null if invalid. |
| `year_raw` | string | Unchanged Bronze `Year`. |
| `industry_aggregation_nzsioc` | string | Published aggregation level; part of observation identity. |
| `industry_code_nzsioc` | string | Published NZSIOC industry code. |
| `industry_name_nzsioc` | string | Published industry label without case normalization. |
| `industry_code_anzsic06` | string | Published textual ANZSIC06 mapping. |
| `variable_code` | string | Published variable code. |
| `variable_name` | string | Published context-dependent variable label. |
| `variable_category` | string | Published variable category. |
| `units` | string | Published units. |
| `value_raw` | string | Unchanged Bronze `Value`, including commas, `C`, and `S`. |
| `value_numeric` | decimal(38,18) | Parsed numeric value only for `PUBLISHED`; otherwise null. |
| `value_status` | string | `PUBLISHED`, `CONFIDENTIAL`, `SUPPRESSED`, `UNAVAILABLE`, or `INVALID`. |
| `record_status` | string | `VALID` when no validation failed; otherwise `INVALID`. |
| `is_valid` | boolean | Whether `validation_rule_ids` is empty. |
| `validation_rule_ids` | array<string> | Stable identifiers for every failed Phase 5 rule. |
| `validation_failure_reasons` | array<string> | Inspectable explanations aligned with the rule IDs. |
| `ingestion_id` | string | Bronze logical ingestion identity. |
| `source_file` | string | Source file path from Bronze. |
| `source_url` | string | Official configured source URL from Bronze. |
| `source_sha256` | string | Source artifact SHA-256 from Bronze. |
| `dataset_year` | integer | Release year metadata from Bronze. |
| `dataset_version` | string | Release/version metadata from Bronze. |
| `ingestion_timestamp` | timestamp | Original logical ingestion timestamp. |
| `source_row_count` | long | Captured source artifact row count. |
| `source_schema_version` | string | Bronze source-contract version. |
| `source_row_number` | long | One-based source data-row position. |
| `silver_schema_version` | string | Implemented Silver contract, currently `aes-silver-v1`. |
| `silver_input_fingerprint` | string | SHA-256 of sorted Bronze artifact identities. |
| `silver_processing_timestamp` | timestamp | First processing time for the persisted logical snapshot. |

Thousands separators are removed only for numeric parsing. Negative values are
valid. Decimal(38,18) was selected because the current values are integers while
the source inspection explicitly warns against assuming future values cannot
contain decimals; `value_raw` remains authoritative if future precision exceeds
the implemented decimal type.

`UNAVAILABLE` can be assigned only to a present Bronze row whose `Value` is null
or blank. Silver does not fabricate rows for source observations that are wholly
absent; that later metric-availability behavior remains defined in the approved
business rules.
