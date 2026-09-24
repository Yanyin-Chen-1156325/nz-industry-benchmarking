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

## Data-quality JSON report

Default location: `data/quality/silver-quality-report.json`

| Field | JSON type | Meaning |
|---|---|---|
| `dataset_path` | string | Assessed Silver Delta location. |
| `generated_at` | string | UTC ISO-8601 report timestamp. |
| `overall_result` | string | `PASS` or `FAIL`; failed blocking checks produce `FAIL`. |
| `rows_processed` | integer | Total Silver rows assessed. |
| `rows_accepted` | integer | Rows with `is_valid = true`. |
| `rows_rejected` | integer | Rows not accepted by the Silver contract. |
| `checks_executed` | integer | Number of checks that ran. |
| `passed_checks` | integer | Checks with status `PASS`. |
| `failed_checks` | integer | Checks with status `FAIL`. |
| `validation_failure_counts` | object | Counts keyed by the original Phase 5 validation rule ID. |
| `checks` | array | Ordered check outcomes described below. |

Each item in `checks` contains `rule_id`, `dimension`, `severity`, `status`,
`description`, `affected_rows`, and `details`. `affected_rows` is null for
schema-level checks and an integer for row checks and informational counts.

## Gold industry financial metrics Delta table

Default location: `data/gold/industry_financial_metrics`

Grain:

```text
gold_input_fingerprint
+ year
+ industry_aggregation_nzsioc
+ industry_code_nzsioc
+ metric_id (M1-M6)
```

The table contains one row for each of M1-M6 for every industry/year identity
observed in Silver. `metric_status` implements M7 for each metric; M7 is not a
separate numeric row.

| Column | Spark type | Meaning |
|---|---|---|
| `metric_record_id` | string | Deterministic SHA-256 identifier for the Gold grain. |
| `year` | integer | Metric financial year. |
| `industry_aggregation_nzsioc` | string | NZSIOC Level 1, Level 3, or Level 4; part of identity. |
| `industry_code_nzsioc` | string | NZSIOC industry code. |
| `industry_name_nzsioc` | string | Current-year published industry name. |
| `industry_code_anzsic06` | string | Current-year published ANZSIC06 mapping. |
| `metric_id` | string | `M1` through `M6`. |
| `metric_name` | string | Approved Phase 1 metric name. |
| `metric_type` | string | `DIRECT` for M1-M3 or `DERIVED` for M4-M6. |
| `metric_value` | decimal(38,18) | Numeric result only when status is `PUBLISHED`. |
| `metric_unit` | string | `NZD millions`, `Percent`, `Percent change`, `NZD millions change`, or `Percentage points`. |
| `metric_status` | string | M7 result: published, protected, unavailable, invalid, unavailable-input, or non-meaningful-base state. |
| `source_variable_code` | string | Exact H01, H23, or H40 source code. |
| `source_variable_name` | string | Exact approved source label. |
| `source_variable_category` | string | Exact approved source category. |
| `source_variable_units` | string | Exact approved AES source units. |
| `current_input_status` | string | Direct/current component status. |
| `current_input_value` | decimal(38,18) | Current component value when published. |
| `current_input_record_ids` | array<string> | Silver record IDs contributing to the current component. |
| `prior_input_status` | string | Immediately preceding-year component status for M4-M6; null for direct metrics. |
| `prior_input_value` | decimal(38,18) | Prior component value when published. |
| `prior_input_record_ids` | array<string> | Silver record IDs contributing to the prior component. |
| `source_silver_record_ids` | array<string> | Union of all contributing Silver record IDs. |
| `source_ingestion_ids` | array<string> | Contributing logical source-ingestion identities. |
| `source_sha256s` | array<string> | Contributing source artifact checksums. |
| `silver_input_fingerprints` | array<string> | Silver snapshot identities represented by the row. |
| `gold_schema_version` | string | Implemented Gold schema, currently `aes-gold-metrics-v1`. |
| `gold_input_fingerprint` | string | Hash of Silver snapshot, Gold schema, and Gold logic versions. |
| `gold_processing_timestamp` | timestamp | First processing time of the persisted logical snapshot. |

Direct metric statuses are `PUBLISHED`, `CONFIDENTIAL`, `SUPPRESSED`,
`UNAVAILABLE`, `INVALID_DUPLICATE`, or `INVALID_VALUE`. Derived statuses are
`PUBLISHED`, `UNAVAILABLE_INPUT`, and, for M4 with a non-positive published
prior value, `NOT_MEANINGFUL_BASE`. Non-published statuses always have a null
`metric_value`.

## Benchmark query result

The Phase 8 result is a read-only, bounded view over
`data/gold/industry_financial_metrics`; it is not a persisted Delta table.
Its grain is:

```text
ranking_type
+ year
+ metric_id (M4-M6)
+ industry_aggregation_nzsioc
+ rank_position
```

Only `PUBLISHED` Gold rows with a non-null value are eligible. The three ranking
types apply their sign and ordering rules without changing the approved Gold
metric or unit.

| Column | Spark type | Meaning |
|---|---|---|
| `ranking_type` | string | `top_increases`, `top_decreases`, or `largest_movements`. |
| `rank_position` | integer | Deterministic one-based ordinal within year, metric, level, and ranking type. |
| `year` | integer | Gold metric year; part of the ranking partition. |
| `industry_aggregation_nzsioc` | string | Gold NZSIOC level; part of the ranking partition. |
| `metric_id` | string | M4, M5, or M6; part of the ranking partition. |
| `metric_name` | string | Approved Gold metric name, unchanged. |
| `metric_unit` | string | Approved Gold unit, unchanged. |
| `metric_status` | string | Always `PUBLISHED` because other Gold states are ineligible for ranking. |
| `industry_code_nzsioc` | string | Published industry code. |
| `industry_name_nzsioc` | string | Published industry name. |
| `metric_value` | decimal(38,18) | Original signed Gold value. |
| `absolute_metric_value` | decimal(38,18) | Absolute value used to order largest movements. |
| `metric_record_id` | string | Gold metric observation identity. |
| `source_silver_record_ids` | array<string> | Contributing Silver record IDs from Gold. |
| `source_ingestion_ids` | array<string> | Contributing logical ingestion IDs from Gold. |
| `source_sha256s` | array<string> | Contributing source artifact checksums from Gold. |
| `silver_input_fingerprints` | array<string> | Silver snapshot identities from Gold. |
| `gold_schema_version` | string | Gold schema contract represented by the row. |
| `gold_input_fingerprint` | string | Gold snapshot identity represented by the row. |
| `gold_processing_timestamp` | timestamp | Original Gold processing time. |

The primary order is signed value descending for increases, signed value
ascending for decreases, and absolute value descending for largest movements.
All ties then use industry code, industry name, and metric record ID ascending.

## Revision audit JSON

Default directory: `data/revisions/`; one file per incoming source SHA-256.

| Field | Meaning |
|---|---|
| `revision_id` | Deterministic identity derived from the revision contract and source artifacts. |
| `overall_result` | `APPLIED`, `DEFERRED_AMBIGUOUS`, `NO_OP`, or `NOT_REVISION`. |
| `precedence_rule` | Exact supported rule used to approve or defer the release. |
| `previous_releases` | Older selected release identities and full source lineage. |
| `incoming_release` | Incoming dataset year/version, artifact SHA-256, URL, path, and ingestion metadata. |
| `overlapping_observations` | Incoming observation identities already represented. |
| `unchanged_republications` | Overlaps whose value and compared metadata are unchanged. |
| `revised_values` | Overlaps whose raw `Value` changed, including protected-state transitions. |
| `revised_metadata` | Overlaps whose published descriptive metadata changed. |
| `newly_added_observations` | Incoming identities absent from the previous current view. |
| `observations_absent_from_incoming` | Previous identities not present in the incoming artifact; not deletions. |
| `current_view_observations_changed` | Revised or new observations affecting the current view. |
| `value_transition_counts` | Counts such as `PUBLISHED->CONFIDENTIAL`. |
| `silver_rebuild_required` | Whether precedence permits a Silver current-view rebuild. |
| `gold_rebuild_required` | Whether Gold must follow the Silver change. |
| `message` | Human-readable outcome explanation. |
