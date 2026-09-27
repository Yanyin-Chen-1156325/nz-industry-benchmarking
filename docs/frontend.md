# Minimal frontend

Phase 13 adds a single-page, read-only consumer of the Phase 12 REST API. It is
implemented with HTML, CSS, and browser ES modules. There is no frontend runtime
framework, state-management library, chart package, or duplicate analytical
store.

## Run locally

First start the API from the repository root, with Java 17 or newer configured:

```powershell
python -m nz_industry_benchmarking.api
```

In a second terminal, build and serve the static frontend:

```powershell
cd frontend
npm run build
python -m http.server 8080 --directory dist
```

Open `http://127.0.0.1:8080` or `http://localhost:8080`. With no build-time
override, the frontend calls the local API at `http://127.0.0.1:8000`.

For a cloud build, supply the public FastAPI URL without committing it:

```powershell
$env:FRONTEND_API_BASE_URL = "https://api.example.test"
npm run build
```

The build writes this value to `dist/config.js`. Browser code receives only the
public FastAPI URL; Databricks hostname, HTTP path, and token remain backend-only
settings.

The API accepts `http://127.0.0.1:8080` and `http://localhost:8080` locally.
Cloud deployment must set the comma-separated `API_CORS_ORIGINS` to the exact
public frontend origin. Wildcard CORS is not enabled.

## User flow

1. Select an NZSIOC aggregation level. The UI requests the matching industry
   catalogue from `GET /api/industries`; no full catalogue is hard-coded.
2. Select an industry and one of its API-provided available years.
3. Review M1-M3 published measures and M4-M6 year-over-year measures.
4. Choose M1-M6 for a compact chronological trend. Each year is a separate row;
   no line connects missing or unavailable values.
5. Choose year, M4-M6, ranking type, and top N for cross-industry benchmarking.

Aggregation level is shared across every view, preventing a screen from mixing
Level 1, Level 3, and Level 4 observations. Benchmarking is the comparison view;
it shows API-provided ranks rather than creating a pairwise or composite score.

## Status and error presentation

Published numbers are formatted for display with their API-provided unit.
Positive benchmark values include a plus sign; negative values keep their minus
sign. The following states are rendered as human-readable text rather than zero:

- `CONFIDENTIAL` -> Confidential
- `SUPPRESSED` -> Suppressed
- `UNAVAILABLE` -> Unavailable
- `UNAVAILABLE_INPUT` -> Required input unavailable
- `NOT_MEANINGFUL_BASE` -> Prior-year base not meaningful
- invalid states -> an explicit invalid/ambiguous source description

Loading, no-data, invalid-request, and API-unavailable states have separate UI
messages. Backend exception details are never displayed.

The data-context card shows only facts supported by the current API: API health,
the selected year, and the number of selected performance metrics that are
published. The Phase 12 contract does not expose the pipeline row count, quality
report result, or processing timestamp, so the frontend does not invent them.

## Frontend boundary

`frontend/js/api-client.js` is the only HTTP access module. It maps responses to
the presentation fields used by the UI and ignores backend metadata. The
frontend source does not import Python, Spark, or Delta code and does not read
local data paths. It performs no M1-M7 calculation and no ranking.

Formatting and status labels live in `frontend/js/formatters.js`; DOM rendering
and user interaction live in `frontend/js/app.js`. This separation allows the
important protected-value, sign, response-mapping, and failure behavior to be
tested without a browser framework.

## Test, check, and build

Node.js is needed only for development verification. No `npm install` step is
required because the frontend has zero third-party packages.

```powershell
cd frontend
npm test
npm run lint
npm run build
```

The build copies the static application to ignored `frontend/dist/` and
generates `dist/config.js` from `FRONTEND_API_BASE_URL`. It does not bundle or
transpile the application.

## Limitations

- This is a focused portfolio UI, not a general dashboard.
- It has no authentication, saved views, export, routing, or client-side cache.
- API availability is process health, not a full pipeline-readiness assertion.
- Data freshness is represented by the selected available AES year because the
  approved API does not publish a separate freshness resource.
