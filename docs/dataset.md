# Dataset discovery: Annual Enterprise Survey 2025

## Dataset identity

| Item | Value |
| --- | --- |
| Dataset name | Annual enterprise survey: 2025 financial year (provisional) |
| Publisher | Stats NZ Tatauranga Aotearoa |
| Release date | 25 June 2026 |
| Reference period for AES 2025 | Balance dates from 1 October 2024 to 30 September 2025 |
| Release status | Provisional |
| Local source file | `data/raw/annual-enterprise-survey-2025-financial-year-provisional.csv` |
| File format | CSV, UTF-8 with BOM |
| File size | 9,525,994 bytes |
| Data rows | 60,255, excluding the header |
| Columns | 10 |
| SHA-256 | `C029D234EEFD3FEE2563B9C0929946CA336509AB62A02BD111C80F978298C66C` |
| Inspection date | 23 September 2026 |

The local file's download metadata identifies the Stats NZ release page as its
referrer and the Stats NZ asset URL below as its download origin. The SHA-256
hash pins the exact local artifact used by this project because the CSV does not
contain an embedded release identifier or version column.

## Official sources

- [Stats NZ release page](https://www.stats.govt.nz/information-releases/annual-enterprise-survey-2025-financial-year-provisional/)
- [Direct CSV download](https://www.stats.govt.nz/assets/Uploads/Annual-enterprise-survey/Annual-enterprise-survey-2025-financial-year-provisional/Download-data/annual-enterprise-survey-2025-financial-year-provisional.csv)
- [2025 release metadata, DataInfo+](https://datainfoplus.stats.govt.nz/item/nz.govt.stats/ded9c5cd-398e-49f1-9f27-8870e354d260)
- [Annual Enterprise Survey 2025 study metadata, DataInfo+](https://datainfoplus.stats.govt.nz/item/nz.govt.stats/adeddde8-848f-4a15-9033-24b883769ba7)
- [Annual Enterprise Survey series methodology and limitations, DataInfo+](https://datainfoplus.stats.govt.nz/item/nz.govt.stats/36809771-984d-4e6b-89a1-576f2118b05b)
- [AES 2025 population metadata, DataInfo+](https://datainfoplus.stats.govt.nz/item/nz.govt.stats/b29ee7c1-3316-45ca-bed0-526ce299d145)
- [Stats NZ symbol definitions](https://www.stats.govt.nz/assets/Tools/Infoshare-help-guide/infoshare-help-guide.pdf)

The release metadata has Stats NZ identifier
`ded9c5cd-398e-49f1-9f27-8870e354d260`, version 1. The 2025 study metadata has
identifier `adeddde8-848f-4a15-9033-24b883769ba7`, version 15. These metadata
versions identify the official records; the local file hash identifies the
downloaded data bytes.

## What the file contains

The CSV contains published, aggregate AES results by financial year, NZSIOC
industry grouping, and published variable. It is not business-level source data.
Stats NZ reports an AES 2025 target population of 548,382 units, while this CSV
contains 60,255 aggregate observations.

The file includes 13 financial years, from 2013 through 2025 inclusive. Each
year has 4,635 rows. The 2025 label refers to businesses whose balance dates
fall within the reference period shown above; it is not necessarily a common
calendar-year reporting period for every business.

## Observed schema and data types

CSV has no native column types, so every field is physically text on read. The
logical types below are observations from all 60,255 rows, not assumptions about
future releases.

| Column | Physical type | Observed logical content | Blank rows | Distinct values |
| --- | --- | --- | ---: | ---: |
| `Year` | text | Four-digit integer-compatible year, 2013–2025 | 0 | 13 |
| `Industry_aggregation_NZSIOC` | text | Categorical aggregation level | 0 | 3 |
| `Industry_code_NZSIOC` | text | NZSIOC industry code; retain as text | 0 | 139 |
| `Industry_name_NZSIOC` | text | Industry label | 0 | 119 |
| `Units` | text | `Dollars`, `Dollars (millions)`, or `Percentage` | 0 | 3 |
| `Variable_code` | text | Published variable code | 0 | 39 |
| `Variable_name` | text | Published variable label | 0 | 41 |
| `Variable_category` | text | Published variable category | 0 | 3 |
| `Value` | text | Numeric text or the marker `C`/`S` | 0 | 15,858 |
| `Industry_code_ANZSIC06` | text | Textual ANZSIC06 mapping/description | 0 | 119 |

Numeric `Value` strings may contain thousands separators and a minus sign. All
57,674 numeric values in this file are integer-valued, but that observation must
not be used to assume that future releases cannot contain decimals. Observed
ranges are:

| Unit | Minimum | Maximum | Negative values |
| --- | ---: | ---: | ---: |
| Dollars | -152,300 | 12,475,500 | 31 |
| Dollars (millions) | -810 | 3,068,548 | 34 |
| Percentage | -50 | 371 | 62 |

Negative values are therefore valid observations in this source and must not be
rejected merely for being below zero.

## Available dimensions

The observed analytical dimensions are:

- Financial year: 2013–2025 inclusive.
- NZSIOC aggregation: `Level 1`, `Level 3`, and `Level 4`.
- NZSIOC industry: code and name.
- ANZSIC06 mapping: a textual code/range description, not a single normalized
  ANZSIC code in every row.
- Variable metadata: code, name, category, and units.

Every year contains 139 industry definitions: 17 at Level 1, 46 at Level 3, and
76 at Level 4. Across the complete file there are 142 distinct tuples of level,
code, name, and ANZSIC06 description because three industry labels change only
in capitalization across years. The affected NZSIOC codes are `OO`, `OO21`, and
`ZZ11`.

There are no dimensions for an individual business, geography, employee-size
band, legal entity, or survey response in this file.

## Available published measures

The source has 39 distinct variable codes and the following 42 distinct
code/name/category/unit definitions. Repeated codes are intentional observations
from the file and are not normalized here.

| Code | Published name | Category | Units |
| --- | --- | --- | --- |
| H01 | Total income | Financial performance | Dollars (millions) |
| H02 | Sales of goods not further processed | Financial performance | Dollars (millions) |
| H03 | Sales of other goods and services | Financial performance | Dollars (millions) |
| H04 | Sales of goods and services | Financial performance | Dollars (millions) |
| H04 | Sales, government funding, grants and subsidies | Financial performance | Dollars (millions) |
| H05 | Interest, dividends and donations | Financial performance | Dollars (millions) |
| H06 | Government funding, grants and subsidies | Financial performance | Dollars (millions) |
| H06 | Sales, government funding, grants and subsidies | Financial performance | Dollars (millions) |
| H07 | Non-operating income | Financial performance | Dollars (millions) |
| H08 | Total expenditure | Financial performance | Dollars (millions) |
| H09 | Interest and donations | Financial performance | Dollars (millions) |
| H10 | Indirect taxes | Financial performance | Dollars (millions) |
| H11 | Depreciation | Financial performance | Dollars (millions) |
| H12 | Salaries and wages paid | Financial performance | Dollars (millions) |
| H13 | Redundancy and severance | Financial performance | Dollars (millions) |
| H14 | Salaries and wages to self employed commission agents | Financial performance | Dollars (millions) |
| H17 | Purchases of goods bought for resale | Financial performance | Dollars (millions) |
| H18 | Other Purchases and operating expenses | Financial performance | Dollars (millions) |
| H18 | Other purchases and operating expenses | Financial performance | Dollars (millions) |
| H19 | Purchases and other operating expenses | Financial performance | Dollars (millions) |
| H20 | Non-operating expenses | Financial performance | Dollars (millions) |
| H21 | Opening stocks | Financial performance | Dollars (millions) |
| H22 | Closing stocks | Financial performance | Dollars (millions) |
| H23 | Surplus before income tax | Financial performance | Dollars (millions) |
| H24 | Total assets | Financial position | Dollars (millions) |
| H25 | Current assets | Financial position | Dollars (millions) |
| H26 | Fixed tangible assets | Financial position | Dollars (millions) |
| H27 | Additions to fixed assets | Financial position | Dollars (millions) |
| H28 | Disposals of fixed assets | Financial position | Dollars (millions) |
| H29 | Other assets | Financial position | Dollars (millions) |
| H30 | Total equity and liabilities | Financial position | Dollars (millions) |
| H31 | Shareholders funds or owners equity | Financial position | Dollars (millions) |
| H32 | Current liabilities | Financial position | Dollars (millions) |
| H33 | Other liabilities | Financial position | Dollars (millions) |
| H34 | Total income per employee count | Financial ratios | Dollars |
| H35 | Surplus per employee count | Financial ratios | Dollars |
| H36 | Current ratio | Financial ratios | Percentage |
| H37 | Quick ratio | Financial ratios | Percentage |
| H38 | Margin on sales of goods for resale | Financial ratios | Percentage |
| H39 | Return on equity | Financial ratios | Percentage |
| H40 | Return on total assets | Financial ratios | Percentage |
| H41 | Liabilities structure | Financial ratios | Percentage |

Category row counts are 30,121 for `Financial performance`, 17,251 for
`Financial position`, and 12,883 for `Financial ratios`. Unit row counts are
47,372 for `Dollars (millions)`, 3,302 for `Dollars`, and 9,581 for
`Percentage`.

`Variable_code` is not a strict one-to-one lookup to `Variable_name` in the raw
file. Codes H04 and H06 each have two materially different observed labels. H18
has two labels differing only by capitalization. Measure availability also
varies by industry, so the 39 variables do not form a complete Cartesian product
with all 139 industries.

No derived business metric is defined in Phase 0. Published financial ratios in
the source are listed above as source variables, not as project-defined formulas.

## Missing values, confidentiality, and suppression

There are no null, empty, or whitespace-only fields in any column. However,
`Value` is a mixed field with semantic non-values:

| Value form | Rows | Meaning |
| --- | ---: | --- |
| Numeric text | 57,674 | Published observation |
| `C` | 2,563 | Confidential |
| `S` | 18 | Suppressed |

Stats NZ applies confidentiality and consequential suppression so published
cells cannot disclose respondent or industry-sensitive information. `C` and `S`
must remain distinct from zero and from ordinary missing/null values. They must
not be coerced to numeric zero.

The `C` rows occur in every year and across all three variable categories and
industry levels. Their category totals are 1,679 financial-performance rows,
505 financial-position rows, and 379 financial-ratio rows. The 18 `S` rows are
all financial-position observations: 2 at Level 1, 2 at Level 3, and 14 at
Level 4. They occur in 2013, 2015, 2016, 2017, 2018, and 2019.

## Observed grain and duplicates

There are no exact duplicate rows. The following candidate key is also unique
across the inspected file:

```text
Year
+ Industry_aggregation_NZSIOC
+ Industry_code_NZSIOC
+ Variable_code
```

This is an observed uniqueness result, not an official Stats NZ declaration and
not yet a final downstream business-key decision. Aggregation level is necessary
because codes and labels must not be assumed globally interchangeable without
their level and published mapping.

## Known limitations and comparability issues

- The release is provisional. Stats NZ states that the latest three AES years
  are provisional and may be revised; exceptional revisions may extend further
  back. The CSV contains no per-row revision/status field.
- AES is designed for industry levels in a given year. Stats NZ advises caution
  below NZSIOC Level 4, and changes in measurement, sample design,
  classification, and collection can affect movements over time.
- Company structure and restructuring can move activity between industries or
  introduce/remove inter-company gross flows. The `All industries` total also
  includes divisional gross flows.
- Rounding and imputation mean component values may not sum exactly to stated
  totals.
- IR10 data does not directly provide some resale, purchases-for-resale, fixed
  asset addition, and disposal estimates. Stats NZ models these items and
  suppresses some lower-quality outputs.
- AES covers economically significant enterprises and excludes some activity,
  including superannuation funds, residential property operators, foreign
  government representation, religious services, private-household activity,
  and non-market central and local government. `All industries` therefore does
  not mean all New Zealand economic activity.
- Published values exclude GST.
- COVID-19 and wage-subsidy effects affect 2020–2023 comparisons. IFRS 16 affects
  lease-related assets, liabilities, depreciation, interest, and operating
  expenses from 2019/2020. IFRS 17 creates a material comparability issue for
  insurance financial-position values from 2024, and AES 2023 was not restated
  for that accounting change.
- Stats NZ improved residential-care and social-assistance data for 2024 and
  2025, particularly fixed assets and other liabilities. Those changes may not
  represent ordinary business movement.
- Three industry names and one H18 variable label vary only by capitalization.
  H04 and H06 have context-dependent labels. Downstream standardization must
  preserve the raw labels and define any mapping explicitly.
- The direct CSV is suitable for programmatic processing, but it does not embed
  its source URL, release identifier, publication timestamp, revision number,
  or file checksum. Pipeline metadata will need to supply those fields in a
  later phase.

## Phase 0 inspection checks

The following checks were run against the complete local file:

- parsed all 60,255 rows and all 10 headers;
- enumerated every year, aggregation level, category, unit, variable code, and
  distinct variable definition;
- checked blank values for every column;
- parsed every numeric `Value` after accounting for thousands separators;
- counted `C` and `S` by year, category, and aggregation level;
- checked exact-row duplicates and observed candidate-key duplicates;
- calculated the file SHA-256 hash;
- compared the file identity and interpretation with official Stats NZ release,
  study, population, series, and symbol metadata.

