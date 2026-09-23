# NZ Industry Benchmarking Data Platform

A portfolio-scale data product for comparing financial performance across New
Zealand industries using the public Stats NZ Annual Enterprise Survey (AES).

The planned platform will demonstrate a production-style Bronze/Silver/Gold
pipeline with Python, PySpark, Delta Lake, Databricks, data-quality controls,
automated tests, and a small REST API. The implementation will stay focused on
industry benchmarking rather than becoming a large dashboard or machine-learning
project.

## Current status

Phase 5 (Silver) is complete. The repository currently contains:

- the inspected AES 2025 provisional CSV in the local `data/raw/` directory;
- documented dataset findings and limitations;
- approved MVP business rules;
- Python packaging, pytest, and Ruff configuration;
- a repeatable raw CSV ingestion command with structured JSON logs;
- an idempotent local ingestion manifest keyed by source SHA-256;
- a PySpark Bronze writer that preserves all raw fields and attaches lineage;
- an idempotent Delta table keyed logically by source SHA-256;
- a typed, validated, one-row-in/one-row-out Silver Delta snapshot;
- reserved API and deployment boundaries for later phases.

No business-metric calculation, Gold processing, API, or deployment workflow has
been implemented yet. The broader quality framework remains a later phase.

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

## Planned architecture

```text
Stats NZ AES CSV
      |
      v
Python ingestion -> Bronze Delta -> PySpark validation -> Silver Delta
                                                            |
                                                            v
                                                        Gold Delta
                                                         /       \
                                                       SQL       API
```

Ingestion and Bronze Delta are implemented. Components after Bronze remain
architectural targets and will be implemented phase by phase.

## Local setup

Python 3.11 or newer and Java 17 or newer are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Runtime dependencies are limited to PySpark and Delta Lake. Development tooling
is installed through the `dev` extra.

## Verification

```powershell
python -m pytest
ruff check .
```

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
|-- scripts/
|-- src/nz_industry_benchmarking/
|   |-- api/
|   |-- bronze/
|   |-- ingestion/
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
