"""Expected revision-handling failures."""


class RevisionError(Exception):
    """Base class for Phase 10 revision failures."""


class RevisionSourceError(RevisionError):
    """Raised when revision history cannot be inspected safely."""
