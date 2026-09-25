"""Errors specific to the deliberately narrow Databricks initial load."""


class DatabricksInitialLoadError(RuntimeError):
    """Raised when existing managed state is outside initial-load scope."""
