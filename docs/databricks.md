# Databricks Free Edition initial load

Phase 15 migration Step 1 prepares the repository for one manual real-data
Bronze -> Silver -> Gold run on Databricks Free Edition Serverless. Free Edition
is used for portfolio/demo purposes, not as a production deployment target.

## Architecture and ownership

Local and Databricks execution import the same Bronze schema, Silver current-view
selection, Silver transformation, quality evaluator, and Gold transformation.
Only runtime ownership and persistence differ:

| Concern | Local | Databricks Free Edition |
|---|---|---|
| Spark lifecycle | `create_spark_session` creates/configures/stops local Spark | The caller passes the platform-provided `spark` |
| Delta identity | Filesystem path | Three-part Unity Catalog table name |
| Read | `spark.read.format("delta").load(...)` | `spark.table(...)` |
| Write | Delta `.save(path)` | Delta `.saveAsTable(name)` |
| Quality output | Existing local JSON service when invoked locally | Returned `QualityReport`; no audit table yet |

`run_initial_load` never selects `local[...]`, installs Maven packages, configures
Spark extensions, accesses `spark.sparkContext`, or stops Spark. The base Python
package also excludes `pyspark` and `delta-spark`; use `local-spark` only on a
developer machine or in CI.

## Scope and safety

This entry point accepts an empty Bronze target or an idempotent rerun of the
same source artifact. It deliberately rejects a managed Bronze table containing
a different ingestion because incremental/revision-state migration is deferred.
Silver and Gold retain their existing deterministic snapshot/idempotency rules.
Quality is evaluated and reported with the existing rules; Step 1 does not yet
persist that report as a managed audit table or make it a new pipeline gate.

Not included: notebooks containing business logic, automated workspace
deployment, Databricks jobs, internet download, Azure integration, Databricks SQL
API access, unattended authentication, or incremental/revision orchestration.

## First manual run

1. Build a wheel locally without bundling dependencies:

   ```powershell
   python -m pip wheel --no-deps --wheel-dir dist .
   ```

2. In Databricks, create or confirm the schema and a Volume for the manually
   downloaded official Stats NZ file:

   ```sql
   CREATE SCHEMA IF NOT EXISTS workspace.nz_industry_benchmarking;
   CREATE VOLUME IF NOT EXISTS workspace.nz_industry_benchmarking.source_files;
   ```

3. Upload the CSV to the Volume, for example
   `/Volumes/workspace/nz_industry_benchmarking/source_files/annual-enterprise-survey-2025-financial-year-provisional.csv`.

4. Upload/install the built project wheel in the Serverless notebook environment.
   Do not install the `local-spark` extra, PySpark, or `delta-spark` there.

5. Use a thin Python notebook cell. The notebook supplies its existing `spark`:

   ```python
   from pathlib import Path

   from nz_industry_benchmarking.databricks import (
       DatabricksInitialLoadConfig,
       run_initial_load,
   )

   config = DatabricksInitialLoadConfig(
       source_file=Path(
           "/Volumes/workspace/nz_industry_benchmarking/source_files/"
           "annual-enterprise-survey-2025-financial-year-provisional.csv"
       ),
       catalog="workspace",
       schema="nz_industry_benchmarking",
       bronze_table="bronze_aes",
       silver_table="silver_aes_observations",
       gold_table="gold_industry_financial_metrics",
   )

   result = run_initial_load(spark, config)
   result.to_dict()
   ```

6. Confirm `result.quality.overall_result`, row counts, and table contents:

   ```sql
   SELECT count(*) FROM workspace.nz_industry_benchmarking.bronze_aes;
   SELECT count(*) FROM workspace.nz_industry_benchmarking.silver_aes_observations;
   SELECT count(*) FROM workspace.nz_industry_benchmarking.gold_industry_financial_metrics;
   ```

The first live run remains a manual verification because this repository has no
access to the owner's Databricks workspace.
