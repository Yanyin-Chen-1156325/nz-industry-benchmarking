# REST API

Phase 12 exposes the approved Gold metrics and Phase 8 rankings through a small,
read-only FastAPI application. It does not calculate metrics, derive
year-over-year values, or implement ranking rules in HTTP handlers.

## Run locally

Install the project dependencies, ensure the configured Gold Delta table exists,
and set Java 17 or newer for PySpark. From the repository root run:

```powershell
python -m nz_industry_benchmarking.api
```

The default address is `http://127.0.0.1:8000`. Configuration is read from
`API_HOST`, `API_PORT`, `API_LOG_LEVEL`, `GOLD_METRICS_PATH`, `SPARK_MASTER`, and
`SPARK_LOG_LEVEL`. The process creates one Spark session for the application
lifespan and stops it at shutdown; it does not create a session per request.

For the Phase 13 local frontend, the API allows
`http://127.0.0.1:8080` and `http://localhost:8080` by default. Override the
comma-separated allowlist with `API_CORS_ORIGINS`. Wildcard CORS is not used.

Interactive OpenAPI documentation is available at `/docs`; the raw OpenAPI
document is at `/openapi.json`.

## Endpoints

### `GET /api/health`

Returns process liveness without querying Spark or Delta:

```json
{"status":"ok"}
```

### `GET /api/industries`

Lists distinct Gold industries and their available years. Optional query
parameters:

- `year`: integer from 1900 through 2100;
- `aggregation_level`: `Level 1`, `Level 3`, or `Level 4`.

### `GET /api/industries/{industry}/performance`

Returns the existing M1-M6 Gold observations for one industry, year, and
aggregation level. Required query parameters are `year` and
`aggregation_level`. The industry path value is the NZSIOC industry code and is
matched case-insensitively after validation.

### `GET /api/industries/{industry}/trend`

Returns existing Gold observations in ascending year order. Required parameters
are `metric_id` (`M1` through `M6`) and `aggregation_level`. Optional
`start_year` and `end_year` bounds filter rows; the API never fills year gaps or
recalculates a metric.

### `GET /api/benchmarks`

Returns a single Phase 8 ranking partition. Required parameters are:

- `year`;
- `metric_id`: `M4`, `M5`, or `M6`;
- `aggregation_level`: `Level 1`, `Level 3`, or `Level 4`;
- `ranking_type`: `top_increases`, `top_decreases`, or `largest_movements`.

`top_n` is optional, defaults to 10, and must be from 1 through 100. The endpoint
delegates to the existing benchmarking query service, so published-only
eligibility, signed values, units, partition separation, and deterministic tie
ordering remain unchanged.

## Metric and status semantics

M1-M6 retain the names and units defined in
[`business-rules.md`](business-rules.md). M7 is represented by `metric_status`
on every metric observation rather than a separate numeric metric row.

Only a `PUBLISHED` observation can have a numeric API `metric_value`. A
`CONFIDENTIAL`, `SUPPRESSED`, `UNAVAILABLE`, `INVALID_DUPLICATE`,
`INVALID_VALUE`, `UNAVAILABLE_INPUT`, or `NOT_MEANINGFUL_BASE` observation is
returned with `metric_value: null` and its actual status. Component statuses are
also returned for direct and derived metrics. Protected values are never
reconstructed or represented as zero.

Every metric result exposes a compact lineage object containing the Gold metric
record ID, contributing Silver record IDs, source ingestion IDs, source SHA-256
identities, and Gold input fingerprint.

## Errors

Errors use one envelope:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request validation failed.",
    "details": [
      {"field": "query.metric_id", "message": "Input should be ..."}
    ]
  }
}
```

| HTTP status | Code | Meaning |
| --- | --- | --- |
| 404 | `NO_MATCHING_DATA` | The request was valid but matched no Gold/ranking rows. |
| 422 | `INVALID_REQUEST` | A parameter or supported-value constraint failed. |
| 503 | `ANALYTICAL_STORAGE_UNAVAILABLE` | Gold Delta or its Spark query failed. |
| 500 | `INTERNAL_ERROR` | An unexpected application failure occurred. |

The 500 and 503 responses contain generic public messages. Local paths,
environment values, Spark/Delta exceptions, stack traces, and other internal
details are logged server-side but are not returned to clients.

## Storage and concurrency boundary

Routes call a framework-independent application service backed by an
`AnalyticsRepository` protocol. Local Spark mode uses `SparkGoldRepository`;
tests can inject an in-memory fake. The Spark repository reads Gold Delta for
financial/trend queries and calls the existing `query_benchmarks` function for
rankings. The Azure production configuration selects the Databricks SQL adapter
described below.

The local API is intended as a portfolio demonstration. It has no write methods,
authentication, response cache, distributed Spark gateway, or availability SLA.
Those concerns require a deployment design and are outside Phase 12.

## Databricks SQL repository adapter

`DatabricksSqlAnalyticsRepository` is also available as a Spark-free adapter to
the same `AnalyticsRepository` contract. It reads the configurable managed Gold
table through `databricks-sql-connector`, maps rows to the existing API records,
and implements the Phase 8 ranking rules in parameterized Databricks SQL.

The local `SparkGoldRepository` remains supported and is still the API startup
default. Set `NZIB_ANALYTICS_BACKEND=databricks-sql` to select the remote
adapter explicitly; `NZIB_ANALYTICS_BACKEND=local-spark` selects the default
local adapter. Any other value fails configuration instead of falling back.

Create `DatabricksSqlConfig` directly or with `from_environment()`. The latter
reads `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, and
`DATABRICKS_TOKEN`; optional identifiers are `DATABRICKS_CATALOG` (default
`workspace`), `DATABRICKS_SCHEMA` (default `nz_industry_benchmarking`), and
`DATABRICKS_GOLD_TABLE` (default `gold_industry_financial_metrics`). Keep all
credentials in the local environment or a secret manager and never commit them
to Git. When `databricks-sql` is selected, all three required connection values
must be present or application construction fails with a sanitized error.
Databricks SQL mode does not initialize or import Spark and is intended for a
lightweight web runtime without PySpark, Delta, or Java. External authenticated
SQL connectivity and the 10,842-row managed Gold table were manually verified
separately; automated tests do not contact Databricks. The Azure App Service
deployment workflow and required external configuration are documented in
[`azure-api-deployment.md`](azure-api-deployment.md); defining the workflow does
not itself perform a deployment.
