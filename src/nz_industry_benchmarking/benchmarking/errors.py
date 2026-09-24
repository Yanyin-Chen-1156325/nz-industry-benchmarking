"""Domain errors raised by Phase 8 benchmarking."""


class BenchmarkError(Exception):
    """Base class for expected benchmarking failures."""


class BenchmarkSourceError(BenchmarkError):
    """Raised when the Gold Delta source cannot be read."""


class BenchmarkSchemaError(BenchmarkError):
    """Raised when Gold does not satisfy the ranking input contract."""
