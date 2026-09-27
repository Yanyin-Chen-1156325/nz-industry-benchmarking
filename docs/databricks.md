# Databricks Free Edition deployment and runbook

The Bronze -> Silver -> Gold pipeline has been manually deployed and executed
against the real Stats NZ Annual Enterprise Survey 2025 provisional dataset in
Databricks Free Edition. The verified compute type is Serverless. This is a
portfolio/demo deployment, not an Azure Databricks deployment.

## Verified architecture

```text
Stats NZ AES CSV
        |
        v
Unity Catalog Volume
        |
        v
Databricks Serverless Python wheel Job
        |
        v
Bronze managed Delta table
        |
        v
Shared Silver transformation
        |
        v
Existing data-quality checks
        |
        v
Shared Gold business metrics
        |
        v
Unity Catalog managed Delta tables / SQL analytics
```

Local and Databricks execution use the same Bronze schema, Silver current-view
selection, Silver transformation, quality evaluator, and Gold transformation.
Only Spark ownership and storage adapters differ:

| Concern | Local development | Databricks Free Edition |
|---|---|---|
| Spark | Locally created PySpark session | Platform-provided Serverless Spark session |
| Delta storage | Filesystem paths | Unity Catalog managed tables |
| Source location | Local file | Unity Catalog Volume |
| Execution | Local commands and pytest | Python wheel Job |
| Quality result | Optional local JSON report | Job result JSON; no audit table yet |

The Databricks wrapper does not create or stop Spark, access
`spark.sparkContext`, or contain transformation formulas.

## Prerequisites and deployed layout

- Databricks Free Edition workspace with Serverless compute.
- Catalog: `workspace`
- Schema: `workspace.nz_industry_benchmarking`
- Volume: `workspace.nz_industry_benchmarking.source_files`
- Source CSV:
  `/Volumes/workspace/nz_industry_benchmarking/source_files/annual-enterprise-survey-2025-financial-year-provisional.csv`
- Wheel:
  `/Volumes/workspace/nz_industry_benchmarking/source_files/packages/nz_industry_benchmarking-0.1.0-py3-none-any.whl`

The wheel is installed as an environment dependency. Databricks supplies Spark
and Delta, so the wheel environment must not install the project's
`local-spark` extra.

The required schema and Volume can be created with:

```sql
CREATE SCHEMA IF NOT EXISTS workspace.nz_industry_benchmarking;
CREATE VOLUME IF NOT EXISTS workspace.nz_industry_benchmarking.source_files;
```

Download the official CSV outside Databricks and upload it to the source path.
The deployed pipeline does not download Stats NZ data from the internet.

## Build and install the wheel

Build from the repository root:

```powershell
python -m pip wheel --no-deps --wheel-dir dist .
```

Upload `nz_industry_benchmarking-0.1.0-py3-none-any.whl` to the `packages`
directory shown above, then add that wheel path as an environment dependency for
the Job.

## Verified Python wheel Job configuration

- Job name: `NZ Industry Benchmarking Pipeline`
- Task type: `Python wheel`
- Compute: `Serverless`
- Schedule/trigger: none; the Job is run manually
- Package name: `nz_industry_benchmarking`
- Entry point: `databricks_job`

Databricks Free Edition resolves these Job fields as a Python import package and
a callable attribute on that package. The package root exposes
`databricks_job()`, which delegates to the existing Databricks job wrapper.

Supply these task parameters as separate arguments:

```text
--source-file
/Volumes/workspace/nz_industry_benchmarking/source_files/annual-enterprise-survey-2025-financial-year-provisional.csv
--catalog
workspace
--schema
nz_industry_benchmarking
--bronze-table
bronze_aes
--silver-table
silver_aes_observations
--gold-table
gold_industry_financial_metrics
```

Only `--source-file` is required. The displayed catalog, schema, and table names
are the configured defaults.

Because AES is an annual source and no automated source acquisition exists, the
current portfolio workflow intentionally has no schedule. Run the Job manually
when an approved source dataset is available in the Volume.

## Run manually

1. Open the `NZ Industry Benchmarking Pipeline` Job.
2. Confirm the wheel environment dependency, Serverless compute, package name,
   entry point, and source-file parameter shown above.
3. Select **Run now**.
4. Inspect the task output JSON for Bronze, Silver, quality, and Gold results.
5. Run the SQL checks below against the managed tables.

## Verified managed tables and results

The successful real-data execution created:

- `workspace.nz_industry_benchmarking.bronze_aes`
- `workspace.nz_industry_benchmarking.silver_aes_observations`
- `workspace.nz_industry_benchmarking.gold_industry_financial_metrics`

Verified row and status counts:

| Layer | Result |
|---|---|
| Bronze | 60,255 input rows; 60,255 total rows |
| Silver | 60,255 input and output rows; 60,255 valid; 0 invalid |
| Silver statuses | 57,674 `PUBLISHED`; 2,563 `CONFIDENTIAL`; 18 `SUPPRESSED` |
| Data quality | 16 checks executed; 16 passed; 0 failed; overall `PASS` |
| Quality rows | 60,255 processed; 60,255 accepted; 0 rejected |
| Gold | 10,842 output rows |
| Gold metrics | M1-M6 each contain 1,807 rows |
| Gold statuses | 10,349 `PUBLISHED`; 32 `CONFIDENTIAL`; 461 `UNAVAILABLE_INPUT` |

Verify all three tables after a run:

```sql
SELECT COUNT(*) FROM workspace.nz_industry_benchmarking.bronze_aes;
SELECT COUNT(*) FROM workspace.nz_industry_benchmarking.silver_aes_observations;
SELECT COUNT(*) FROM workspace.nz_industry_benchmarking.gold_industry_financial_metrics;
```

The verified Gold query returned `10,842`:

```sql
SELECT COUNT(*)
FROM workspace.nz_industry_benchmarking.gold_industry_financial_metrics;
```

## Verified idempotent rerun

The same Job was run again against the same CSV. The second successful run
reported:

- Bronze: `duplicate: true`, 60,255 input rows, 0 inserted rows, 60,255 total
  rows.
- Silver: `duplicate: true`, 60,255 output rows.
- Gold: `duplicate: true`, 10,842 output rows.
- Data quality: overall `PASS`, with 16 of 16 checks passed.

This verifies that rerunning this already-ingested source does not duplicate
Bronze records and that the Silver and Gold snapshots are reused. It does not
prove every future incremental or revision scenario; managed-state migration
for those workflows remains deferred.

## Naming troubleshooting

The similar names have different purposes:

| Name type | Value | Use |
|---|---|---|
| Python distribution | `nz-industry-benchmarking` | Package metadata/build identity |
| Python import package | `nz_industry_benchmarking` | `import nz_industry_benchmarking` |
| Console script | `nz-industry-benchmarking-databricks` | Normal installed command-line execution |
| Free Edition Job package name | `nz_industry_benchmarking` | Verified Job UI value |
| Free Edition Job entry point | `databricks_job` | Verified package-level callable |

Using the distribution name and hyphenated console-script name in the verified
Free Edition Job UI caused Databricks to interpret the entry point as a Python
attribute expression and fail. Use `nz_industry_benchmarking` and
`databricks_job` for this environment.

## Deferred work

This deployment does not include scheduled ingestion, automated workspace
deployment, credentials in the repository, a managed quality audit table,
Databricks SQL API integration, Azure App Service, Azure Databricks, or the full
incremental/revision workflow on managed storage.
