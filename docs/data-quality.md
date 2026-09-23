# Data quality

The dataset's observed characteristics are documented in
[`dataset.md`](dataset.md). Phase 5 implements the row-level checks needed to
produce a safe Silver representation; it does not implement the broader Phase 6
quality framework or pipeline-level PASS/FAIL reporting.

## Implemented Silver checks

Silver validates:

- exact Bronze columns and logical types before transformation;
- required observation dimensions and lineage fields;
- four-digit year format;
- the observed `Level 1`, `Level 3`, and `Level 4` aggregation values;
- exact variable code/name/category/unit tuples documented in Phase 0;
- numeric, `C`, `S`, null/blank, and invalid value forms;
- observation uniqueness by ingestion, year, aggregation level, NZSIOC code,
  and variable code;
- uniqueness and range of `source_row_number`;
- Bronze row-count metadata against actual rows per ingestion;
- equality of `ingestion_id` and `source_sha256`.

The variable definition check intentionally uses the full four-field tuple. It
does not assume `Variable_code` maps globally to one name: both H04 meanings,
both H06 meanings, and both H18 capitalization variants are allowed exactly as
published.

## Value status

| Source `Value` condition | `value_numeric` | `value_status` | Row validity |
|---|---:|---|---|
| Valid numeric text | Parsed decimal | `PUBLISHED` | Valid unless another rule fails |
| Exact `C` | null | `CONFIDENTIAL` | Valid unless another rule fails |
| Exact `S` | null | `SUPPRESSED` | Valid unless another rule fails |
| Null, empty, or whitespace-only | null | `UNAVAILABLE` | Invalid and inspectable |
| Any other text or decimal overflow | null | `INVALID` | Invalid and inspectable |

Negative numeric values remain `PUBLISHED`. Protected values are never inferred
from other measures and are never converted to zero.

## Invalid records

Silver never filters a Bronze record. Each failed row contains:

- stable `record_id` and source lineage;
- `record_status = INVALID` and `is_valid = false`;
- all applicable `validation_rule_ids`;
- aligned `validation_failure_reasons`;
- `silver_processing_timestamp` and Silver schema/input identity.

This makes rejected or unusable rows queryable in the same Delta table. A
separate rejected table is unnecessary for the implemented one-row-in/one-row-out
Silver model.
