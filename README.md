# NZ Industry Benchmarking Data Platform

An end-to-end data engineering platform built with public Stats NZ Annual Enterprise Survey data, using Databricks, PySpark, and Delta Lake to transform raw statistical data into reliable, traceable, and consumable industry financial data products.

> **Live Demo:** [https://nz-industry-benchmarking.vercel.app/](https://nz-industry-benchmarking.vercel.app/)

## Key Results

| Outcome | Verified result |
| --- | --- |
| Source processing | 60,255 Stats NZ AES observations |
| Data quality | 16 / 16 checks passed |
| Curated output | 60,255 Silver rows and 10,842 Gold metric rows |
| Idempotency | Same-source rerun inserted 0 Bronze rows and reused Silver / Gold |
| Data platform | Databricks Serverless, Delta Lake, and Unity Catalog |
| Data serving | Databricks SQL Warehouse and FastAPI on Azure App Service |
| Delivery | GitHub Actions CI/CD using OIDC federation to Azure |
| User interface | HTML / CSS / JavaScript frontend deployed on Vercel |

---

## Overview

The **NZ Industry Benchmarking Data Platform** is a portfolio-scale data engineering project built using the **Stats NZ Annual Enterprise Survey (AES): 2025 financial year (provisional)** dataset.

It implements a deployed path from raw CSV ingestion through Bronze, Silver,
and Gold managed Delta tables to a Databricks SQL-backed API and web frontend.
The project demonstrates source validation, PySpark transformations, data
quality and contracts, lineage, idempotent processing, revision handling,
industry benchmarking, automated testing, and cloud delivery.

The resulting data product enables users to compare financial performance across New Zealand industries, explore historical trends, and identify significant year-over-year changes.

---

## Business Problem

The Stats NZ Annual Enterprise Survey provides extensive financial statistics about New Zealand industries.

However, raw statistical data still requires validation, standardisation, business-rule transformation, and appropriate handling of protected values before it can be reliably consumed by analytical tools or applications.

This project addresses four core business questions:

1. How does financial performance compare across New Zealand industries?
2. How has an industry's financial performance changed over time?
3. Which financial indicators changed the most?
4. Can users trust the published results?

All business metrics are derived from fields available in the inspected AES dataset. The project does not create metrics that cannot be supported by the source data.

---

## Data Source

**Dataset:** Stats NZ — Annual Enterprise Survey: 2025 financial year (provisional)

The project uses publicly released aggregate industry data rather than business-level or private administrative data.

The dataset contains:

- Data from 2013 to 2025
- 60,255 source observations
- Multiple NZSIOC industry aggregation levels
- Financial measures
- Confidential (`C`) values
- Suppressed (`S`) values

The official Stats NZ CSV is not committed to the Git repository.

Dataset schema, source information, checksum, dimensions, measures, and known limitations are documented in:

[`docs/dataset.md`](docs/dataset.md)

---

## Architecture

The verified deployed path is:

```text
Stats NZ AES CSV in a Unity Catalog Volume
        |
        v
Databricks Serverless Job
        |
        v
Bronze Managed Delta
        |
        v
Silver Managed Delta + Data Quality
        |
        v
Gold Managed Delta
        |
        v
Databricks SQL Warehouse
        |
        v
FastAPI / Azure App Service
        |
        v
HTML / CSS / JavaScript Frontend / Vercel
```

Within the pipeline, Silver preserves source states and validation metadata;
Gold applies the approved M1-M7 business contract. The API serves existing Gold
metric, trend, and M4-M6 benchmark results rather than recalculating them.

---

## Data Pipeline

### Bronze Layer

The Bronze layer preserves the Stats NZ source data with minimal transformation and provides the foundation for traceability.

It:

- Preserves all source fields
- Retains raw values as text
- Records ingestion metadata
- Calculates the source SHA-256
- Adds row-level lineage
- Stores data in Delta format
- Prevents duplicate logical ingestion of the same source

SHA-256 is used to identify the actual source artifact, so source identity does not depend on the filename.

### Silver Layer

The Silver layer uses PySpark to standardise and validate Bronze data.

Processing includes:

- Year parsing
- Numeric conversion
- Missing-value handling
- Confidential value handling
- Suppressed value handling
- Invalid-state classification
- Duplicate detection
- Validation metadata

Silver follows a **one-row-in / one-row-out** design.

Source observations are not silently discarded because they are protected, unavailable, or invalid. Their values and validation states remain traceable through the pipeline.

### Gold Layer

The Gold layer transforms validated Silver observations into business metrics that directly support analytics and API consumption.

The current metric contract includes:

| Metric | Description |
| --- | --- |
| M1 | Total Income |
| M2 | Surplus Before Income Tax |
| M3 | Return on Total Assets |
| M4 | Total Income YoY Change |
| M5 | Surplus Before Income Tax YoY Change |
| M6 | Return on Total Assets YoY Change |
| M7 | Metric Availability Status |

The main Gold grain is:

```text
Silver Snapshot
+ Year
+ NZSIOC Aggregation Level
+ Industry
+ Metric
```

Confidential, suppressed, unavailable, or invalid observations are not converted to zero. Their status remains explicit in the Gold data product.

---

## Data Quality

Data quality is part of the pipeline rather than an after-the-fact validation step.

The quality framework covers:

- Schema validation
- Completeness checks
- Data type validation
- Value validation
- Business-key uniqueness
- Metric contract validation
- Statistical status handling

Verified results for the real AES dataset:

| Measure | Result |
| --- | ---: |
| Rows processed | 60,255 |
| Rows accepted | 60,255 |
| Rows rejected | 0 |
| Confidential observations | 2,563 |
| Suppressed observations | 18 |
| Negative published values | 127 |
| Data quality checks | **16 / 16 PASS** |

Legitimate confidential, suppressed, and negative published values are identified and tracked without being incorrectly treated as data-quality failures.

The complete quality rules are documented in:

[`docs/data-quality.md`](docs/data-quality.md)

---

## Industry Benchmarking

The Gold data product supports cross-industry and year-over-year benchmarking.

The benchmarking layer provides three ranking modes:

- **Top Increases** — industries with the largest positive year-over-year changes
- **Top Decreases** — industries with the largest negative year-over-year changes
- **Largest Movements** — industries with the largest absolute changes while retaining the signed value

Benchmarking is limited to published M4-M6 metrics.

Every comparison is isolated by:

- Year
- Metric
- NZSIOC aggregation level

This prevents values with different units or aggregation levels from being incorrectly compared.

---

## Incremental Processing

The pipeline uses source SHA-256 and downstream fingerprints to determine whether processing is required.

Each processing layer can be classified as:

```text
CURRENT
REQUIRED
DEFERRED
```

The overall planner returns:

```text
NO_OP
PROCESS_REQUIRED
DEFERRED_REVISION
```

When exactly the same source is processed again:

```text
First Run
    |
    v
Process Source
    |
    v
Bronze -> Silver -> Gold

Second Run
    |
    v
Same Source SHA-256
    |
    v
No Duplicate Bronze Rows
    |
    v
Reuse Existing Silver / Gold
```

This provides idempotent processing and avoids unnecessary downstream work.

---

## Revision Handling

Published statistical datasets may be revised after their initial release.

The pipeline therefore distinguishes between new data and revised statistical releases.

Bronze retains source history, while Silver selects the current observation according to explicit release-precedence rules.

```text
Source Releases
      |
      v
Bronze History
      |
      v
Current Silver Snapshot
      |
      v
Gold Metrics
```

Release precedence uses the approved `dataset_year` rather than inferring authority from:

- Filename
- Ingestion timestamp
- SHA-256
- Free-form version text

This allows historical source lineage and revision audit information to remain traceable.

---

## REST API

The Gold data product is exposed through a read-only FastAPI application
deployed on Azure App Service. In cloud mode, the backend uses
`databricks-sql-connector` to query the managed Gold table through a Databricks
SQL Warehouse; it does not require Spark, Delta, or Java in the web runtime.

The API supports:

- `GET /api/health`
- `GET /api/industries`
- `GET /api/industries/{industry}/performance`
- `GET /api/industries/{industry}/trend`
- `GET /api/benchmarks`

It provides:

- Typed response models
- Request validation
- Consistent HTTP errors
- OpenAPI documentation
- Gold metric status preservation

Protected or unavailable observations are represented explicitly, for example:

```json
{
  "metric_value": null,
  "metric_status": "CONFIDENTIAL"
}
```

rather than being incorrectly represented as zero.

Cloud integration was verified against the real Gold data. The deployed API
returned 2025 financial metrics for Manufacturing (`CC`), and the verified
routes include health, industry catalogue, performance, trend, and benchmark
queries.

The complete API contract is documented in:

[`docs/api.md`](docs/api.md)

---

## Web Application

The project includes a lightweight HTML / CSS / JavaScript frontend deployed on
Vercel. It consumes Gold data only through the FastAPI application and never
connects directly to Databricks.

Users can:

- Select an industry
- Select a year
- View M1-M6 financial metrics
- Explore historical trends
- View industry rankings
- See data availability status

The frontend is intentionally small. Its purpose is to demonstrate the complete consumption path:

```text
Data Pipeline
      |
      v
Gold Data Product
      |
      v
REST API
      |
      v
Web Application
```

**Live application:**
[https://nz-industry-benchmarking.vercel.app/](https://nz-industry-benchmarking.vercel.app/)

---

## Databricks Deployment

The Bronze → Silver → Gold pipeline has been deployed and verified on **Databricks Free Edition using Serverless compute**.

The deployment uses:

- Python Wheel
- Databricks Job
- Serverless compute
- Unity Catalog Volume
- Unity Catalog managed Delta tables

Verified results from the real AES 2025 provisional dataset:

| Measure | Result |
| --- | ---: |
| Source rows | 60,255 |
| Silver rows | 60,255 |
| Data quality checks | **16 / 16 PASS** |
| Gold metric rows | 10,842 |

An idempotent rerun of the same dataset produced:

| Measure | Result |
| --- | ---: |
| New Bronze rows | 0 |
| Silver snapshot | Reused |
| Gold snapshot | Reused |

This verifies the pipeline's data processing and idempotent behaviour in a Databricks environment.

The Databricks Job is currently triggered manually. Scheduled execution and
automated Databricks workspace deployment are outside the current project scope.

Detailed Databricks configuration and verification steps are documented in:

[`docs/databricks.md`](docs/databricks.md)

---

## Automated Testing

The project includes:

- Unit tests
- Transformation tests
- Data quality tests
- Contract tests
- Integration tests
- API tests
- Frontend tests

Current test coverage includes:

- **134 Python tests**
- **8 frontend tests**

Integration tests validate the processing path:

```text
CSV
 |
 v
Ingestion
 |
 v
Bronze
 |
 v
Silver
 |
 v
Gold
```

Tests use synthetic fixtures and temporary Delta paths, so the normal CI suite does not require the full official AES dataset.

---

## Continuous Integration / Deployment

GitHub Actions automatically validates the project on pull requests and pushes to `main`.

CI is separated into:

```text
Fast Backend Checks
        +
Spark / Delta Tests
        +
Frontend Test / Lint / Build
```

The CI environment uses:

- Python 3.13
- Java 17
- Node.js 22

CI does not require Databricks credentials or the official Stats NZ CSV.

This keeps source-code validation independent from cloud deployment credentials.

Successful push-triggered CI runs on `main` continue through the API deployment
workflow:

```text
Push to main
      |
      v
GitHub Actions CI
      |
      v
Fast backend + Spark / Delta + frontend validation
      |
      v
CI success
      |
      v
deploy-api
      |
      v
GitHub OIDC + Azure managed identity
      |
      v
Azure App Service
```

The deployment checks out the exact CI-verified commit and builds a
self-contained Python deployment package from `pyproject.toml`. Azure/Oryx does
not install from `requirements.txt`. Authentication uses short-lived OIDC
federation; no Azure client secret, publish profile, or Databricks token is
stored in GitHub. The Databricks token remains an Azure App Service setting.

---

## Technology Stack

| Area | Technology |
| --- | --- |
| Programming | Python |
| Data Processing | PySpark |
| Data Platform | Databricks Free Edition / Serverless |
| Storage | Delta Lake |
| Data Catalog | Unity Catalog |
| Query | Databricks SQL Warehouse / PySpark |
| API | FastAPI / Azure App Service |
| Testing | pytest |
| Linting | Ruff |
| CI/CD | GitHub Actions / GitHub OIDC / Azure Managed Identity |
| Frontend | HTML / CSS / JavaScript / Vercel |
| Packaging | Python Wheel |
| Version Control | Git / GitHub |

---

## Key Engineering Decisions

### Preserve Statistical Meaning

Confidential, suppressed, missing, and invalid observations are not simply converted to zero.

### Separation of Concerns

Ingestion, validation, transformation, quality checks, and business logic are separated so that each stage has a clear responsibility.

### Idempotent Processing

Source identity and processing fingerprints are used to prevent unnecessary duplicate processing.

### Data Lineage

Source and processing metadata are retained so that Gold results can be traced back through the pipeline.

### Dataset-Driven Business Rules

Business metrics are implemented only when they are supported by the inspected AES dataset.

### Quality as Part of the Pipeline

Data quality is integrated into the processing workflow rather than treated as a final manual check.

---

## Limitations

This is a portfolio-scale data platform rather than a production Stats NZ system.

Current limitations include:

- Only publicly available AES aggregate data is used
- No Stats NZ internal or private administrative data sources are used
- Databricks Free Edition is used for the cloud data pipeline
- The Databricks Job is manually triggered
- Production scheduling is not configured
- Production monitoring and alerting infrastructure is not implemented
- Automated Databricks deployment is not implemented
- Only one inspected real Stats NZ source release is currently available, so the revision framework has not yet been validated against multiple real revised releases

These limitations are documented explicitly to avoid presenting a portfolio implementation as a production system.

---

## Future Improvements

Potential future improvements include:

- Databricks Asset Bundles
- Automated Databricks deployment
- Scheduled Databricks Workflows
- Production monitoring and alerting
- Additional AES releases
- Additional revision scenarios
- Additional governed Gold data products
