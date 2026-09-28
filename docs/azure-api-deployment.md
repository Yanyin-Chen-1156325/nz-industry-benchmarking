# Azure App Service API deployment

The FastAPI backend is prepared for deployment to the Linux Azure Web App
`nz-industry-benchmarking-api`. The application uses Python 3.13 and the
Databricks SQL analytics backend. This workflow deploys only the API; it does
not deploy the frontend or run the Databricks data pipeline.

## Runtime configuration

Configure the Web App stack as Linux Python 3.13 and retain this startup
command:

```text
python -m nz_industry_benchmarking.api
```

Configure these Azure App Settings:

| Name | Production purpose |
|---|---|
| `NZIB_ANALYTICS_BACKEND` | Set to `databricks-sql`. |
| `DATABRICKS_SERVER_HOSTNAME` | Databricks SQL server hostname. |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path. |
| `DATABRICKS_TOKEN` | Databricks credential supplied from Azure secret configuration. |
| `DATABRICKS_CATALOG` | Unity Catalog catalog containing Gold data. |
| `DATABRICKS_SCHEMA` | Unity Catalog schema containing Gold data. |
| `DATABRICKS_GOLD_TABLE` | Gold metrics table name. |
| `API_HOST` | Set to `0.0.0.0` so App Service can reach Uvicorn. |
| `API_PORT` | Uvicorn listening port, currently `8000`. |
| `API_LOG_LEVEL` | Production API log level. |
| `API_CORS_ORIGINS` | Exact public frontend origin; do not use a wildcard. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | Set to `false`; dependencies are already in the deployment package. |

Keep `DATABRICKS_TOKEN` in Azure configuration backed by the chosen secret
management process. It must not be stored in this repository, the deployment
artifact, GitHub Actions, or frontend configuration. The browser communicates
only with FastAPI.

The production API does not need `SPARK_MASTER`, `SPARK_LOG_LEVEL`, local Delta
paths, Java, PySpark, or `delta-spark`.

## GitHub OIDC configuration

Create or select a Microsoft Entra application/service principal and grant it
only the Azure role and scope needed to deploy the Web App. Add a federated
identity credential for the repository's `production` GitHub Environment. Its
subject must match:

```text
repo:<github-owner>/<github-repository>:environment:production
```

Use the GitHub OIDC audience `api://AzureADTokenExchange`. In the GitHub
`production` Environment, define these variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

These identifiers enable short-lived OIDC authentication. Do not add a client
secret, publish profile, Azure password, Databricks token, or combined Azure
credentials JSON to GitHub.

Environment protection rules and required reviewers may be added to
`production`. If approval is required, the workflow waits after build
validation and before receiving an Azure OIDC token.

## Deployment workflow

`.github/workflows/deploy-api.yml` listens for completion of the existing `CI`
workflow on `main`. The deploy job runs only when that CI run:

1. was triggered by a push;
2. completed successfully; and
3. belongs to `main`.

The workflow checks out the exact commit SHA validated by CI. It does not rerun
the Spark/Delta or frontend suites. On a clean Python 3.13 runner it installs
the project and its base dependencies into `deployment-package/` with:

```text
python -m pip install --target deployment-package .
```

This is a self-contained App Service package containing the installed
`nz_industry_benchmarking` package, FastAPI, Uvicorn, the Databricks SQL
connector, and their transitive dependencies. The workflow deliberately does
not install the `local-spark` or `dev` extras. It verifies the application can
be constructed in `databricks-sql` mode without importing Spark or Delta, then
uses `azure/login` with OIDC and `azure/webapps-deploy` to deploy the directory
to the `Production` slot.

Azure/Oryx dependency installation is intentionally disabled for this model.
There is no `requirements.txt`, editable installation, or partially duplicated
build step on the Web App.

## Verification

After the GitHub deployment job succeeds, check App Service logs for a clean
Uvicorn startup and request:

```text
https://nz-industry-benchmarking-api.azurewebsites.net/api/health
```

The expected response is:

```json
{"status":"ok"}
```

The health endpoint proves process liveness and does not query Databricks. Also
call a read-only data endpoint to verify the App Settings, outbound network
access, SQL warehouse availability, and Gold table permissions. A 503 from a
data endpoint indicates the API is running but its analytical storage is not
available.
