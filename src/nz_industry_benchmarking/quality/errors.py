"""Errors raised by the Phase 6 quality command boundary."""


class QualityError(Exception):
    """Base error for expected quality command failures."""


class QualitySourceError(QualityError):
    """Raised when the configured Silver source cannot be assessed."""
