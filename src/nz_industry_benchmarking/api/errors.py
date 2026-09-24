"""Stable API/application errors that do not expose storage details."""


class ApiQueryError(RuntimeError):
    """Base class for expected API query failures."""


class NoMatchingDataError(ApiQueryError):
    """A valid query matched no analytical observations."""


class AnalyticalStorageError(ApiQueryError):
    """Gold storage or its Spark query boundary is unavailable."""
