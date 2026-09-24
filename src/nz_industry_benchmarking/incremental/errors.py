"""Expected Phase 9 incremental-processing failures."""


class IncrementalError(Exception):
    """Base class for incremental pipeline errors."""


class IncrementalStateError(IncrementalError):
    """Raised when persisted pipeline state cannot be inspected safely."""
