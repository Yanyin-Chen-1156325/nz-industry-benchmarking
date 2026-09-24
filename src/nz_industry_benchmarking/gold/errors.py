"""Gold processing error types."""


class GoldError(Exception):
    """Base error for expected Gold failures."""


class GoldSourceError(GoldError):
    """Raised when the configured Silver source cannot be used."""


class GoldSchemaError(GoldError):
    """Raised when Silver does not match its implemented contract."""


class GoldIntegrityError(GoldError):
    """Raised when persisted Gold state conflicts with expected state."""
