"""NZ Industry Benchmarking Data Platform."""

__version__ = "0.1.0"


def databricks_job() -> None:
    """Delegate a Databricks package-function task to the wheel job wrapper."""
    from nz_industry_benchmarking.databricks.job import main

    main()
