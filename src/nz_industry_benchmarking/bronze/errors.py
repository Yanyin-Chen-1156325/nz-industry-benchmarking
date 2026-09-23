"""Expected failures raised by the Bronze persistence boundary."""


class BronzeError(Exception):
    """Base class for Bronze-layer failures."""


class BronzeIntegrityError(BronzeError):
    """Raised when stored rows conflict with ingestion metadata."""
