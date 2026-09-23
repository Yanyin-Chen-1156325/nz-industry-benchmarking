"""Expected errors raised by Silver processing."""


class SilverError(Exception):
    """Base class for Silver-layer failures."""


class SilverSourceError(SilverError):
    """Raised when the configured Bronze Delta input is unavailable."""


class SilverSchemaError(SilverError):
    """Raised when Bronze does not match the implemented source contract."""


class SilverIntegrityError(SilverError):
    """Raised when a stored Silver snapshot is incomplete or conflicting."""
