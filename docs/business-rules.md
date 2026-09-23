# Business rules: focused MVP metrics

## Scope

This document defines the Phase 1 metric contract for the NZ Industry
Benchmarking Data Platform. It is based on the inspected Stats NZ AES file
documented in [`dataset.md`](dataset.md). It defines business rules only; no
pipeline, table, API, or executable metric implementation is included in this
phase.

The MVP uses three published AES measures, three year-over-year changes derived
from them, and one non-financial availability indicator:

| ID | Metric | Type |
| --- | --- | --- |
| M1 | Total income | Published value |
| M2 | Surplus before income tax | Published value |
| M3 | Return on total assets | Published value |
| M4 | Total income year-over-year growth | Derived value |
| M5 | Surplus before income tax year-over-year change | Derived value |
| M6 | Return on total assets year-over-year change | Derived value |
| M7 | Metric availability status | Quality indicator |

This set is deliberately small. Total income represents activity scale, surplus
before income tax represents the absolute financial result, and return on total
assets provides a published percentage measure that is more suitable for
comparison between differently sized industries. Their changes support trend
and largest-movement analysis. Availability status makes protected or absent
data visible rather than silently converting it to zero.

## Common selection and calculation rules

### Observation identity

Every metric observation is scoped by:

```text
Year
+ Industry_aggregation_NZSIOC
+ Industry_code_NZSIOC
```

`Industry_name_NZSIOC` and `Industry_code_ANZSIC06` are descriptive attributes.
The aggregation level is part of the identity: Level 1, Level 3, and Level 4
must not be mixed, summed together, or treated as peer industries in the same
ranking.

### Source-value parsing

- Select a source measure by exact `Variable_code` and verify its expected
  `Variable_name`, `Variable_category`, and `Units`.
- Remove comma thousands separators before parsing numeric `Value` text.
- Preserve the source value at full available precision for calculation.
- Display derived percentages to two decimal places and percentage-point
  changes to one or two decimal places. Display rounding must not replace the
  stored calculation value.
- Negative numeric values are valid. They are not missing and must not be
  rejected solely because they are negative.
- More than one row for the same observation identity and variable code is an
  invalid/ambiguous input. Do not select one silently.

### Confidential, suppressed, and unavailable inputs

The following rules apply to every metric:

| Source condition | Numeric result | Status |
| --- | --- | --- |
| Numeric `Value` | Parsed/calculated value | `PUBLISHED` |
| `Value = C` | null | `CONFIDENTIAL` |
| `Value = S` | null | `SUPPRESSED` |
| Expected source row absent | null | `UNAVAILABLE` |
| Duplicate source rows at the expected grain | null | `INVALID_DUPLICATE` |
| Present but unparseable value other than `C`/`S` | null | `INVALID_VALUE` |

`C`, `S`, missing rows, and zero are different states. Neither `C` nor `S` may
be replaced with zero or included in an aggregate calculation.

For a derived metric, every required input must be numeric and `PUBLISHED`. If
any input is not published, the derived numeric result is null, its status is
`UNAVAILABLE_INPUT`, and the status of each input must remain available for
explanation (for example, `current=CONFIDENTIAL`, `prior=PUBLISHED`).

### Year-over-year comparability

Year-over-year metrics compare the same industry code at the same aggregation
level in year `t` and year `t - 1`. A gap is not bridged: if the immediately
preceding year is absent or nonnumeric, the result is unavailable. The first
available year for an industry has no year-over-year result.

The calculation can establish a numeric change, but it cannot prove that the
change is purely economic. Known classification, methodology, accounting, and
survey changes described in `dataset.md` must remain visible as data caveats.

## M1: Total income

### Business meaning

Total income is the published AES measure of an industry's overall income. It
provides an absolute measure of industry activity scale. It is not renamed
`revenue`, because the source explicitly calls it `Total income`.

### Exact AES inputs

| Field | Required value/use |
| --- | --- |
| `Variable_code` | `H01` |
| `Variable_name` | `Total income` |
| `Variable_category` | `Financial performance` |
| `Units` | `Dollars (millions)` |
| `Value` | Published numeric value or status marker |
| Dimensions | `Year`, `Industry_aggregation_NZSIOC`, `Industry_code_NZSIOC` |

### Formula

```text
total_income_nzd_millions = numeric(Value for H01)
```

This is a direct published measure, not a sum of other AES variables.

### Unit

NZD millions, as published by Stats NZ.

### Protected, missing, or unavailable inputs

Apply the common status rules. A numeric zero remains zero. `C`, `S`, an absent
H01 row, an unexpected unit, or an invalid value produces no numeric result and
must carry the applicable status.

### Example

For Manufacturing (`CC`, Level 1) in 2025, the source H01 value is `134105`:

```text
Total income = NZD 134,105 million
```

## M2: Surplus before income tax

### Business meaning

Surplus before income tax is the published AES absolute financial result before
income tax. It may be positive, zero, or negative. It is not relabelled as
`operating profit`, because that is not the source variable's name.

### Exact AES inputs

| Field | Required value/use |
| --- | --- |
| `Variable_code` | `H23` |
| `Variable_name` | `Surplus before income tax` |
| `Variable_category` | `Financial performance` |
| `Units` | `Dollars (millions)` |
| `Value` | Published numeric value or status marker |
| Dimensions | `Year`, `Industry_aggregation_NZSIOC`, `Industry_code_NZSIOC` |

### Formula

```text
surplus_before_income_tax_nzd_millions = numeric(Value for H23)
```

This is a direct published measure.

### Unit

NZD millions, as published by Stats NZ.

### Protected, missing, or unavailable inputs

Apply the common status rules. A negative value is a valid deficit-like result,
not an error. A `C` or `S` value must remain protected and must not be inferred
from related fields.

### Example

For Construction (`EE`, Level 1) in 2025, the source H23 value is `6410`:

```text
Surplus before income tax = NZD 6,410 million
```

## M3: Return on total assets

### Business meaning

Return on total assets is Stats NZ's published percentage measure of the return
generated relative to total assets. It provides a size-normalized performance
indicator for comparing industries.

The project uses the published H40 value. It does not reverse-engineer or
replace Stats NZ's calculation with `H23 / H24`, because the CSV does not define
the official ratio formula or its averaging and adjustment rules.

### Exact AES inputs

| Field | Required value/use |
| --- | --- |
| `Variable_code` | `H40` |
| `Variable_name` | `Return on total assets` |
| `Variable_category` | `Financial ratios` |
| `Units` | `Percentage` |
| `Value` | Published numeric value or status marker |
| Dimensions | `Year`, `Industry_aggregation_NZSIOC`, `Industry_code_NZSIOC` |

### Formula

```text
return_on_total_assets_percent = numeric(Value for H40)
```

This is a direct published ratio. No project-defined financial formula is
applied.

### Unit

Percent.

### Protected, missing, or unavailable inputs

Apply the common status rules. Negative percentages are valid source values.
Do not calculate a replacement ratio when H40 is `C`, `S`, or absent, because
doing so could defeat source confidentiality or differ from Stats NZ's method.

### Example

For Construction (`EE`, Level 1) in 2025, the source H40 value is `9`:

```text
Return on total assets = 9 percent
```

## M4: Total income year-over-year growth

### Business meaning

This metric shows the percentage change in total income for the same industry
from the immediately preceding financial year. It supports comparisons of
growth direction and magnitude without using absolute industry size alone.

### Exact AES inputs

Two M1 observations for the same aggregation level and industry code:

- current-year H01 `Value` at year `t`;
- prior-year H01 `Value` at year `t - 1`.

Both inputs retain the exact H01 field requirements defined for M1.

### Formula

```text
if prior_total_income > 0:
    total_income_yoy_growth_percent =
        ((current_total_income - prior_total_income) / prior_total_income) * 100
else:
    total_income_yoy_growth_percent = null
```

A non-positive prior value does not produce a conventional growth rate and is
reported with status `NOT_MEANINGFUL_BASE`.

### Unit

Percent change from the immediately preceding financial year.

### Protected, missing, or unavailable inputs

If either H01 input is `C`, `S`, absent, duplicated, or invalid, apply the
derived-metric rule and return no growth value. Do not skip to an earlier year.
If the prior numeric value is zero or negative, return no percentage and use
`NOT_MEANINGFUL_BASE`.

### Example

Manufacturing (`CC`, Level 1) total income was NZD 127,567 million in 2024 and
NZD 134,105 million in 2025:

```text
((134,105 - 127,567) / 127,567) * 100 = 5.13 percent
```

## M5: Surplus before income tax year-over-year change

### Business meaning

This metric shows the absolute change in surplus before income tax for the same
industry from the immediately preceding financial year. Absolute change is used
instead of a growth percentage because surplus can validly be zero or negative;
a percentage around zero or across a sign change can be misleading.

### Exact AES inputs

Two M2 observations for the same aggregation level and industry code:

- current-year H23 `Value` at year `t`;
- prior-year H23 `Value` at year `t - 1`.

Both inputs retain the exact H23 field requirements defined for M2.

### Formula

```text
surplus_yoy_change_nzd_millions =
    current_surplus_nzd_millions - prior_surplus_nzd_millions
```

### Unit

NZD millions change from the immediately preceding financial year.

### Protected, missing, or unavailable inputs

If either H23 input is `C`, `S`, absent, duplicated, or invalid, apply the
derived-metric rule and return no change value. Numeric zero and negative
surplus values remain valid calculation inputs.

### Example

Construction (`EE`, Level 1) surplus before income tax was NZD 8,216 million in
2024 and NZD 6,410 million in 2025:

```text
6,410 - 8,216 = -1,806
```

The 2025 year-over-year change is therefore a decrease of NZD 1,806 million.

## M6: Return on total assets year-over-year change

### Business meaning

This metric shows how the published return on total assets changed for the same
industry from the immediately preceding financial year. The difference is
expressed in percentage points, not percent, because H40 is already a percentage.

### Exact AES inputs

Two M3 observations for the same aggregation level and industry code:

- current-year H40 `Value` at year `t`;
- prior-year H40 `Value` at year `t - 1`.

Both inputs retain the exact H40 field requirements defined for M3.

### Formula

```text
return_on_assets_yoy_change_percentage_points =
    current_return_on_assets_percent - prior_return_on_assets_percent
```

### Unit

Percentage points change from the immediately preceding financial year.

### Protected, missing, or unavailable inputs

If either H40 input is `C`, `S`, absent, duplicated, or invalid, apply the
derived-metric rule and return no change value. A published zero or negative
percentage remains a valid input.

### Example

Construction (`EE`, Level 1) return on total assets was 12 percent in 2024 and
9 percent in 2025:

```text
9 - 12 = -3 percentage points
```

## M7: Metric availability status

### Business meaning

Metric availability status tells users whether a requested value is usable and,
if not, why it is unavailable. It is a data-trust indicator, not a financial
performance measure. It prevents protected, missing, or invalid observations
from appearing as zeros.

### Exact AES inputs

For M1–M3, use the existence and `Value` of the selected H01, H23, or H40 row at
the required observation identity. For M4–M6, use the statuses of both the
current- and prior-year source observations. Expected `Units`, category, name,
and uniqueness are also validated under the common rules.

### Formula

For a direct metric:

```text
numeric and valid                         -> PUBLISHED
Value = C                                 -> CONFIDENTIAL
Value = S                                 -> SUPPRESSED
row absent                                -> UNAVAILABLE
duplicate observation                     -> INVALID_DUPLICATE
other nonnumeric or metadata mismatch     -> INVALID_VALUE
```

For a derived metric:

```text
all required inputs PUBLISHED             -> PUBLISHED
any required input not PUBLISHED          -> UNAVAILABLE_INPUT
M4 prior-year numeric value <= 0           -> NOT_MEANINGFUL_BASE
```

When a derived status is `UNAVAILABLE_INPUT`, the component statuses are
retained so a user can distinguish confidentiality, suppression, and absence.

### Unit

Categorical status; no numeric unit.

### Protected, missing, or unavailable inputs

The status is the handling mechanism. It must be returned even when the numeric
metric is null. The original `C` or `S` marker must remain traceable internally
and must not be exposed as an inferred value.

### Example

For Basic Chemical and Basic Polymer Manufacturing (`CC521`, Level 4) in 2023,
H23 is `C`:

```text
surplus_before_income_tax_nzd_millions = null
metric_status = CONFIDENTIAL
```

Any 2023 year-over-year surplus change requiring that value is null with
`metric_status = UNAVAILABLE_INPUT` and a retained component status of
`current=CONFIDENTIAL`.

## Largest-change and ranking rules

For a selected year pair, industries may be ranked within the same NZSIOC
aggregation level using:

- absolute M4 value for largest total-income growth or decline;
- absolute M5 value for largest surplus movement;
- absolute M6 value for largest return-on-assets movement.

Only `PUBLISHED` derived metrics participate. Rankings must remain separate by
metric because percent, NZD millions, and percentage points are not comparable
units. The platform must not produce a single cross-unit score or claim that a
NZD movement is inherently larger than a percentage-point movement.

## Mapping metrics to business questions

| Project business question | Supporting metrics | How they support it |
| --- | --- | --- |
| 1. How does the financial performance of different industries compare? | M1, M2, M3, M7 | Compare activity scale and absolute surplus side by side, then use published return on assets for a size-normalized view; expose unavailable values. |
| 2. How has an industry's financial performance changed over time? | M1–M6, M7 | Plot published levels and their immediate year-over-year changes while retaining status and comparability caveats. |
| 3. Which financial indicators changed the most? | M4, M5, M6, M7 | Produce separate same-unit rankings for income growth, absolute surplus change, and return-on-assets movement. |
| 4. Can users trust the published results? | M7, applied to M1–M6 | Preserve confidentiality/suppression, reject invalid inputs, expose missing components, and avoid fabricated zeros or ratios. |

## Phase 1 verification examples

These expected results were manually checked against the actual CSV. They are
the acceptance examples to automate when metric implementation and tests are
authorized in a later phase.

| Metric | Source observation(s) | Expected result |
| --- | --- | --- |
| M1 | Manufacturing, Level 1, 2025, H01 = 134105 | NZD 134,105 million; `PUBLISHED` |
| M2 | Construction, Level 1, 2025, H23 = 6410 | NZD 6,410 million; `PUBLISHED` |
| M3 | Construction, Level 1, 2025, H40 = 9 | 9 percent; `PUBLISHED` |
| M4 | Manufacturing H01: 2024 = 127567, 2025 = 134105 | 5.13 percent; `PUBLISHED` |
| M5 | Construction H23: 2024 = 8216, 2025 = 6410 | -1,806 NZD millions; `PUBLISHED` |
| M6 | Construction H40: 2024 = 12, 2025 = 9 | -3 percentage points; `PUBLISHED` |
| M7 | CC521, Level 4, 2023, H23 = C | null; `CONFIDENTIAL` |

No executable tests are added in Phase 1 because this phase is documentation
only and the approved scope explicitly excludes implementation. Each rule has a
concrete source-backed expected result ready to become a test case later.

## Decisions and exclusions

- `Total income` is used instead of inventing a `revenue` field.
- `Surplus before income tax` is kept under its source meaning and is not called
  operating profit.
- Published H40 is used for return on total assets. The project does not infer
  Stats NZ's formula from H23 and H24.
- A project-defined profit margin is not included in the MVP. The source's H38
  is specifically `Margin on sales of goods for resale`, not a general profit
  margin, and inventing a broader label would be misleading.
- Salary ratios and liability ratios are excluded to keep the MVP focused. They
  can be reconsidered only if a later business requirement justifies them.
- Surplus change uses an absolute amount rather than a percentage because valid
  zero and negative surplus values make percentage growth difficult to
  interpret.
- No cross-unit composite score is defined. Largest-change results are reported
  separately for each metric.

