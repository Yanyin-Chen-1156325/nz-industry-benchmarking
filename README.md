# NZ Industry Benchmarking Data Platform

A portfolio-scale data product for comparing financial performance across New
Zealand industries using the public Stats NZ Annual Enterprise Survey (AES).

The planned platform will demonstrate a production-style Bronze/Silver/Gold
pipeline with Python, PySpark, Delta Lake, Databricks, data-quality controls,
automated tests, and a small REST API. The implementation will stay focused on
industry benchmarking rather than becoming a large dashboard or machine-learning
project.

## Current status

Phase 14 (CI/CD) is complete. The repository currently contains:

- the inspected AES 2025 provisional CSV in the local `data/raw/` directory;
- documented dataset findings and limitations;
- approved MVP business rules;
- Python packaging, pytest, and Ruff configuration;
- a repeatable raw CSV ingestion command with structured JSON logs;
- an idempotent local ingestion manifest keyed by source SHA-256;
- a PySpark Bronze writer that preserves all raw fields and attaches lineage;
- an idempotent Delta table keyed logically by source SHA-256;
- a typed, validated, one-row-in/one-row-out Silver Delta snapshot;
- a PySpark quality framework with stable blocking and informational rules;
- an inspectable JSON quality report with overall PASS/FAIL and row counts;
- a Gold Delta metric fact table implementing the approved M1-M7 contract;
- a read-only PySpark query layer for M4-M6 increases, decreases, and movements;
- dependency-aware SHA-256/fingerprint planning with safe revision deferral;
- release-aware Bronze history, Silver current-view selection, and revision audit;
- a risk-mapped unit, data-quality/contract, and integration test strategy;
- a typed read-only FastAPI over Gold metrics, trends, and Phase 8 rankings;
- generated OpenAPI documentation and safe, consistent HTTP errors;
- a responsive static frontend for performance, trends, statuses, and rankings;
- GitHub Actions validation with separate fast, Spark/Delta, and frontend jobs;
- reserved deployment boundaries for later phases.

Deployment is deferred to Phase 15; no deployment workflow or credentials have
been added.

## Business questions

The final product is intended to answer:

1. How does financial performance compare across industries?
2. How has an industry's financial performance changed over time?
3. Which financial indicators changed the most?
4. Can users trust the published results?

The approved MVP uses Stats NZ's published total income (H01), surplus before
income tax (H23), and return on total assets (H40), plus focused year-over-year
changes and an explicit availability status.

## Data source

The source is **Annual enterprise survey: 2025 financial year (provisional)**,
published by Stats NZ Tatauranga Aotearoa. The local CSV contains aggregate
industry observations for 2013–2025. It is not business-level data.

See [dataset discovery](docs/dataset.md) for the exact source, schema, checksum,
confidentiality markers, and limitations. See
[business rules](docs/business-rules.md) for the approved metrics.

The CSV is intentionally ignored by Git. Download it from the official URL in
`.env.example` and place it at the configured `AES_SOURCE_FILE` path.

## Raw ingestion

Run the Phase 3 ingestion command from the repository root:

```powershell
python -m nz_industry_benchmarking.ingestion
```

The command:

- reads the configured AES CSV as UTF-8 CSV;
- enforces the Phase 0 header contract;
- preserves every source field, including `Value`, as text;
- calculates the exact source-file SHA-256;
- records source, dataset, row-count, timestamp, and schema metadata;
- emits structured JSON logs;
- writes one logical record per source artifact to
  `data/ingestion/manifest.json`.

The manifest and CSV are local artifacts and are ignored by Git. Re-running the
command for the same source hash returns `status: duplicate`, retains the first
logical ingestion timestamp, and does not add another manifest record.

Defaults come from the values documented in `.env.example`. Settings can be
exported as environment variables or overridden with CLI options; use
`python -m nz_industry_benchmarking.ingestion --help` for the complete list.
The project does not automatically parse a local `.env` file and therefore does
not require a dotenv runtime dependency.

## Bronze Delta

Install Java 17 or newer, set `JAVA_HOME`, and run from the repository root:

```powershell
python -m nz_industry_benchmarking.bronze
```

The command uses the approved ingestion output as its source boundary, creates a
PySpark DataFrame with every source column kept as a string, adds ingestion and
row-lineage metadata, and writes Delta format to `data/bronze/aes` by default.
Re-running the same source SHA-256 reports `duplicate: true`, inserts zero rows,
and verifies that the previously stored logical ingestion is complete.

Python 3.11+ is supported. Phase 4 pins PySpark 4.2.0 and Delta Lake 4.4.0 because
those releases are mutually compatible and support the project's local Python
3.13 environment. Spark 4.2 requires Java 17 or newer. No Pandas or PyArrow extras
are needed for this row-preserving Bronze implementation.

Configuration is available through the variables in `.env.example` or CLI
arguments; use `python -m nz_industry_benchmarking.bronze --help` for details.
The local source, ingestion manifest, Bronze table, and `.tools` directory are
ignored by Git.

Delta normally resolves its JVM artifacts from Maven on first use. In an offline
or certificate-intercepted environment, `DELTA_SPARK_LOCAL_JARS` can point to an
isolated directory containing compatible Delta runtime JARs; it is not needed in
a normal environment. Do not point it at a broad dependency cache containing
conflicting Spark libraries.

Native Windows local-file Delta writes also require Hadoop's Windows native
runtime (`winutils.exe`). This repository's Phase 4 Delta write and tests were
verified with Ubuntu WSL instead, using the same project code and an isolated
Java/Python environment. Linux and Databricks do not have the Windows-specific
`winutils.exe` requirement.

After writing Bronze, the implemented verification command is:

```powershell
python scripts/verify_bronze.py
```

It reads the Delta table and reports its row count, exact column contract,
source-column types, `C`/`S` counts, and distinct ingestion metadata.

## Silver processing

Run the Bronze-only Silver transformation with:

```powershell
python -m nz_industry_benchmarking.silver
```

Silver parses year and numeric values, preserves raw values and labels,
classifies `C`, `S`, unavailable, and invalid states, and attaches inspectable
validation outcomes. Every Bronze row remains present. Reprocessing the same set
of Bronze artifacts verifies and skips the existing logical snapshot.

The default output is `data/silver/aes_observations`. Verify it with:

```powershell
python scripts/verify_silver.py
```

## Data quality

Assess the persisted Silver Delta table with:

```powershell
python -m nz_industry_benchmarking.quality
```

The command checks schema, completeness, validity, uniqueness, and contract
consistency. It prints and atomically persists a JSON report at
`data/quality/silver-quality-report.json` by default. A failed blocking check
returns overall `FAIL` and CLI exit code 1. Legitimate `C`, `S`, and negative
published values are validated and counted but do not fail the dataset.

The actual AES Silver snapshot passed all 16 checks: 60,255 rows processed,
60,255 accepted, and zero rejected. Informational counts were 2,563
confidential, 18 suppressed, and 127 negative published rows. See
[data quality](docs/data-quality.md) for every rule and its severity.

## Gold analytics

Calculate the approved M1-M7 business metrics from Silver with:

```powershell
python -m nz_industry_benchmarking.gold
```

The command writes one long-format Delta table to
`data/gold/industry_financial_metrics`. Its grain is Silver snapshot, year,
NZSIOC aggregation level, industry code, and metric ID. M1-M3 are exact H01,
H23, and H40 published measures; M4-M6 compare only the immediately preceding
year for the same aggregation level and industry. `metric_status` implements M7
and keeps protected, unavailable, invalid, and non-meaningful results explicit.

The actual snapshot contains 10,842 rows: 1,807 rows for each of M1-M6. Verify
the grain, statuses, lineage, and Phase 1 acceptance examples with:

```powershell
python scripts/verify_gold.py
```

Re-running unchanged Silver input reports `duplicate: true` and retains the
first persisted Gold processing timestamp.

## Industry benchmarking

Query the Gold Delta table without creating another persisted copy:

```powershell
python -m nz_industry_benchmarking.benchmarking `
  --year 2025 `
  --metric-id M4 `
  --aggregation-level "Level 1" `
  --ranking-type top_increases `
  --top-n 5
```

Supported ranking types are `top_increases` (positive values descending),
`top_decreases` (negative values ascending), and `largest_movements` (absolute
magnitude descending while returning the signed value). Only `PUBLISHED` M4,
M5, or M6 rows are eligible. Every ranking is isolated by year, metric, and
NZSIOC aggregation level, so units and aggregation levels never mix.

Equal primary values are ordered by industry code, industry name, then Gold
`metric_record_id`, all ascending. `rank_position` is therefore a stable unique
ordinal rather than a shared competition rank. Run actual-data verification:

```powershell
python scripts/verify_benchmarks.py
```

The bounded JSON result is used by the API adapter and retains Gold and source
lineage. The query layer is intentionally read-only: there is no benchmark
Delta table to synchronize or deduplicate.

## REST API

Start the read-only FastAPI application after Gold has been created:

```powershell
python -m nz_industry_benchmarking.api
```

The default API is served at `http://127.0.0.1:8000`, with interactive OpenAPI
documentation at `/docs`. It exposes health, available industries, annual
performance, chronological trends, and M4-M6 benchmark rankings. One Spark
session is shared for the application lifespan; request handlers do not create
sessions or implement metric/ranking formulas.

Protected and otherwise non-published observations retain their Gold status and
serialize with `metric_value: null`, never zero. Validation, no-data, storage,
and unexpected failures use consistent safe error bodies. See the complete
[API contract](docs/api.md).

## Minimal frontend

Serve the dependency-free browser client in a second terminal while the API is
running:

```powershell
python -m http.server 5173 --directory frontend
```

Open `http://127.0.0.1:5173`. The UI obtains aggregation-specific industries and
available years from the API, presents M1-M6 performance and chronological
trends, and supports all three M4-M6 ranking modes. Protected and unavailable
values appear as named statuses rather than zero.

Set the API base URL in `frontend/config.js`; set the matching explicit API
origin allowlist through `API_CORS_ORIGINS`. See the [frontend guide](docs/frontend.md)
for behavior, local commands, tests, and limitations.

## Incremental processing

Run the existing stages only when their effective inputs changed:

```powershell
python -m nz_industry_benchmarking.incremental
```

The planner uses source SHA-256 rather than filename identity. It reports each
layer as `CURRENT`, `REQUIRED`, or `DEFERRED`, and returns an overall `NO_OP`,
`PROCESS_REQUIRED`, or `DEFERRED_REVISION` result. An unchanged current source
does not invoke any Bronze, Silver, or Gold writer.

New artifacts with no observation-grain overlap are appended once to Bronze;
the existing deterministic Silver and Gold snapshot writers rebuild only when
their effective input fingerprints are stale. Any overlap with Bronze is safely
deferred because release precedence belongs to Phase 10. See
[incremental operations](docs/incremental-processing.md) for exact behavior and
limitations.

Verify that the actual AES source and all downstream layers are current:

```powershell
python scripts/verify_incremental.py
```

## Revision handling

Process an officially identified newer release that Phase 9 deferred because it
overlaps existing observations:

```powershell
python -m nz_industry_benchmarking.revision
```

Release precedence uses only the approved integer `dataset_year`: it must be
strictly greater for every overlapping current observation. Filename, SHA-256,
ingestion time, and free-form version text are never sorted to invent authority.
Equal-year artifacts remain `DEFERRED_AMBIGUOUS`.

Bronze retains both source artifacts. Silver selects one current row per AES
observation grain, while prior lineage remains in Bronze and the revision audit
under `data/revisions/`. Missing observations are retained from the previous
release, not treated as deletions. Gold rebuilds only after the effective Silver
snapshot changes. See [revision handling](docs/revision-handling.md).

The repository contains only one inspected real Stats NZ artifact. Verify that
it remains unchanged and produces no revision write with:

```powershell
python scripts/verify_revision.py
```

## Architecture

```text
Stats NZ AES CSV
      |
      v
Python ingestion -> Bronze Delta -> PySpark validation -> Silver Delta
                                                            |
                                                            v
                                                    Quality PASS/FAIL
                                                            |
                                                            v
                                                  M1-M7 Gold Delta
                                                         |
                                              +----------+----------+
                                              |                     |
                                              v                     v
                                       Metric/trend queries   Benchmark queries
                                                                    (M4-M6)
                                              |                     |
                                              +----------+----------+
                                                         v
                                                   REST API
                                                         |
                                                         v
                                                Minimal frontend
```

Ingestion, Bronze, Silver, quality, Gold metrics, benchmarking, incremental
planning, revision handling, automated testing, and the REST API are
implemented together with the minimal frontend. Deployment components remain
later-phase targets.

## Local setup

Python 3.11 or newer and Java 17 or newer are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Runtime dependencies are PySpark, Delta Lake, FastAPI, and Uvicorn. PySpark and
Delta implement the analytical storage boundary; FastAPI provides typed OpenAPI
and request validation; Uvicorn runs the ASGI application. Pytest, Ruff, and the
HTTPX2 test client are installed through the `dev` extra.

The frontend has no third-party packages. Node.js is used only for its built-in
test runner, JavaScript syntax checks, and the copy-only static build.

## Verification

```powershell
python -m pytest
ruff check .
```

The Phase 13 backend suite contains 67 collected tests: 47 unit, 9
data-quality/contract, and 11 integration cases. Five additional Node tests cover
the frontend API adapter and presentation rules. The suites use synthetic
fixtures and temporary Delta paths;
the normal suite does not process the full official AES file. The Phase 9 and
Phase 10 integration cases provide the end-to-end smoke path across CSV
ingestion, Bronze, Silver, and Gold. See the [testing strategy](docs/testing.md)
for the inventory, coverage decisions, isolation guarantees, and intentional
limitations.

## Continuous integration

GitHub Actions runs on pull requests and pushes to `main`. Independent jobs
provide fast backend feedback, one non-duplicated Spark/Delta test pass, and the
existing dependency-free frontend test/lint/build checks. CI uses Python 3.13,
Java 17, and Node.js 22 and never requires the ignored official AES CSV. See the
[CI guide](docs/ci.md) for exact commands, triggers, permissions, dependency
resolution, and the Phase 15 deployment boundary.

## Repository structure

```text
.
|-- .github/workflows/              # CI workflows added in Phase 14
|-- data/raw/                       # Local official source file; CSV ignored
|-- databricks/
|   |-- bronze/
|   |-- silver/
|   `-- gold/
|-- docs/
|-- frontend/                       # Static Phase 13 API consumer
|-- scripts/
|-- src/nz_industry_benchmarking/
|   |-- api/
|   |-- benchmarking/
|   |-- bronze/
|   |-- gold/
|   |-- incremental/
|   |-- ingestion/
|   |-- quality/
|   |-- revision/
|   |-- silver/
|   |-- transformation/
|   `-- validation/
|-- tests/
|   |-- data_quality/
|   |-- integration/
|   `-- unit/
|-- .env.example
`-- pyproject.toml
```

The directories mark component boundaries; empty areas are reserved for their
approved implementation phases.
