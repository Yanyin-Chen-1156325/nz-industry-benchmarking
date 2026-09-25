# Continuous integration

Phase 14 adds one GitHub Actions workflow at `.github/workflows/ci.yml`. It
validates pull requests and pushes to `main`; it does not deploy the application.
Azure and Databricks deployment remain Phase 15 work because no deployment
infrastructure or credentials are part of Phase 14.

## Workflow structure

The workflow has three independent jobs:

| Job | Runtime | Validation |
|---|---|---|
| `Backend / fast` | Python 3.13 | Ruff, every Spark-free pytest case, and a backend wheel build |
| `Backend / Spark and Delta` | Python 3.13, Temurin Java 17 | Every test that uses the shared local Spark/Delta session |
| `Frontend` | Node.js 22 | `npm test`, `npm run lint`, and `npm run build` |

The workflow runs for every pull request and every push to `main`. Path filters
are intentionally not used: the repository is small, and shared Python, test,
workflow, documentation, and frontend configuration can affect more than one
job. The workflow grants only read access to repository contents, defines no
secrets, disables persisted checkout credentials, pins GitHub-maintained actions
to immutable release commit SHAs, and cancels an older run for the same branch
or pull request.

## Fast and Spark feedback

Tests that directly or transitively request the session-scoped `spark` fixture
receive the registered `spark` marker during collection. This classifies tests
by their actual runtime requirement rather than their directory: Spark-backed
unit and data-quality tests run with the Delta integration job, while
Spark-free integration cases run in the fast job.

The two selections are complementary, so no test is duplicated:

```text
python -m pytest -m "not spark"
python -m pytest -m spark
```

The Spark job resolves the JVM Delta package declared by `delta-spark` from the
configured Maven Central repository on a clean GitHub-hosted Linux runner. It
does not set `DELTA_SPARK_LOCAL_JARS` and does not rely on WSL, a pre-existing
Maven cache, Windows paths, or `winutils.exe`.

## Dependency reproducibility

The backend's direct runtime and development dependencies and setuptools build
backend are pinned in `pyproject.toml`. GitHub Actions installs the project from
that repository declaration. PySpark 4.2.0 and Delta Lake 4.4.0 use Java 17 in
CI. Python 3.13 matches the supported local project environment.

The frontend has no third-party dependencies, so CI does not run `npm install`
or introduce a lockfile. Node.js 22 supplies the built-in test runner and syntax
checker. Its copy-only build writes `frontend/dist/` on the disposable runner;
that directory is ignored by Git and is not uploaded or committed.

Normal CI uses only synthetic pytest fixtures. It neither downloads nor reads
the ignored official AES CSV and does not write generated Bronze, Silver, Gold,
quality, or revision artifacts outside pytest temporary directories.

## Local equivalents

From an activated environment created with Python 3.13 and Java 17:

```powershell
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -m "not spark"
python -m pip wheel --no-deps --wheel-dir dist .
python -m pytest -m spark
```

Run the frontend commands separately:

```powershell
Set-Location frontend
npm test
npm run lint
npm run build
```

The backend wheel in `dist/`, frontend output in `frontend/dist/`, pytest state,
and all local data products are intentionally ignored. GitHub-hosted success can
only be claimed after the workflow has been pushed and completed on GitHub;
local execution validates the underlying commands and workflow configuration,
not the hosted runner itself.
