# Data quality

Phase 6 implements a small PySpark quality framework over the Silver Delta
dataset. It reuses the Phase 5 Silver value and validation semantics documented
in [`dataset.md`](dataset.md) and [`business-rules.md`](business-rules.md); it
does not clean, filter, or rewrite Silver records.

Run the assessment with:

```powershell
python -m nz_industry_benchmarking.quality
```

The command reads `SILVER_TABLE_PATH` and atomically writes an inspectable JSON
report to `QUALITY_REPORT_PATH`. Defaults are `data/silver/aes_observations` and
`data/quality/silver-quality-report.json`.

## Result and severity semantics

Every check has a stable, human-readable rule ID, quality dimension, severity,
PASS/FAIL status, affected-row count where applicable, and details.

- `BLOCKING` checks contribute to the overall result. Any failed blocking check
  makes the report `FAIL`.
- `INFORMATIONAL` checks report legitimate source characteristics and never
  make the report fail.

Schema failure stops dependent row checks because their columns or types cannot
be used safely. The report still contains the three executed schema outcomes,
the input row count, and overall `FAIL`.

## Implemented rules

| Rule ID | Dimension | Severity | Purpose |
|---|---|---|---|
| `DQ_SCHEMA_REQUIRED_COLUMNS` | Schema | Blocking | Detect missing implemented Silver columns. |
| `DQ_SCHEMA_UNEXPECTED_COLUMNS` | Schema | Blocking | Detect undocumented added columns. |
| `DQ_SCHEMA_COLUMN_TYPES` | Schema | Blocking | Enforce implemented Spark logical types. |
| `DQ_COMPLETENESS_REQUIRED_DIMENSIONS` | Completeness | Blocking | Require year, industry, variable, and unit dimensions. |
| `DQ_VALIDITY_YEAR` | Validity | Blocking | Require consistent four-digit raw and typed years. |
| `DQ_VALIDITY_AGGREGATION_LEVEL` | Validity | Blocking | Allow only observed Level 1, Level 3, and Level 4 values. |
| `DQ_VALIDITY_VARIABLE_DEFINITION` | Business contract | Blocking | Validate the full code/name/category/unit tuple, including valid H04, H06, and H18 variants. |
| `DQ_VALIDITY_VALUE_STATE` | Validity | Blocking | Validate agreement among raw value, parsed decimal, and Silver value status. |
| `DQ_UNIQUENESS_RECORD_ID` | Uniqueness | Blocking | Detect duplicate stable record identifiers. |
| `DQ_UNIQUENESS_OBSERVATION_GRAIN` | Uniqueness | Blocking | Detect duplicates by ingestion, year, aggregation level, NZSIOC industry, and variable code. |
| `DQ_CONTRACT_VALIDATION_OUTCOME` | Business contract | Blocking | Check consistency of validity flags, status, rule IDs, and reasons. |
| `DQ_CONTRACT_INVALID_ROWS` | Business contract | Blocking | Count records rejected by the implemented Silver contract. |
| `DQ_CONTRACT_LINEAGE` | Business contract | Blocking | Validate source/processing lineage, source-row coverage, versions, and identifiers. |
| `DQ_INFO_CONFIDENTIAL_ROWS` | Informational | Informational | Count valid `CONFIDENTIAL` observations. |
| `DQ_INFO_SUPPRESSED_ROWS` | Informational | Informational | Count valid `SUPPRESSED` observations. |
| `DQ_INFO_NEGATIVE_PUBLISHED_ROWS` | Informational | Informational | Count valid negative published values. |

The value-state check considers these mappings valid:

| `value_status` | Required representation |
|---|---|
| `PUBLISHED` | Numeric `value_raw` and non-null `value_numeric` |
| `CONFIDENTIAL` | `value_raw = C` and null `value_numeric` |
| `SUPPRESSED` | `value_raw = S` and null `value_numeric` |
| `UNAVAILABLE` | Blank/null `value_raw` and null `value_numeric` |
| `INVALID` | Present unusable raw value and null `value_numeric` |

`UNAVAILABLE` and `INVALID` are valid representations under the value-state
check, but their rows remain rejected by the Silver contract and therefore fail
`DQ_CONTRACT_INVALID_ROWS`. The report's `validation_failure_counts` preserves
the underlying Phase 5 rule IDs, such as `VALUE_INVALID` or
`VARIABLE_DEFINITION_UNEXPECTED`, so the reason remains traceable. Original
rows remain queryable in Silver with their rule IDs and failure reasons.

`CONFIDENTIAL`, `SUPPRESSED`, and valid negative values are not quality
failures. They are checked for correct representation and counted separately by
informational rules. Protected values are never inferred or converted to zero.

## Actual AES result

The framework was executed against the implemented Silver AES snapshot:

| Result field | Observed value |
|---|---:|
| Overall result | `PASS` |
| Rows processed | 60,255 |
| Rows accepted | 60,255 |
| Rows rejected/invalid | 0 |
| Checks executed | 16 |
| Passed checks | 16 |
| Failed checks | 0 |
| Confidential rows | 2,563 |
| Suppressed rows | 18 |
| Negative published rows | 127 |

All 13 blocking checks passed: three schema checks matched the contract and ten
row-level blocking checks reported zero affected rows. All three informational
checks passed and reported the legitimate source-state counts above.

## Limitations

- The assessment verifies the present Silver snapshot; it does not prove the
  economic accuracy of Stats NZ published values.
- Variable metadata is intentionally an exact contract. A new official source
  definition will fail until it is reviewed and added deliberately.
- The framework verifies completeness of rows that exist in Silver. It does not
  infer a full expected industry/variable Cartesian product because measure
  availability varies by industry.
- A schema failure prevents dependent row checks from running. This is a safe
  fail-fast boundary, not silent acceptance.
- Cross-year comparability caveats remain those documented in `dataset.md`;
  Phase 6 does not calculate trends or business metrics.
