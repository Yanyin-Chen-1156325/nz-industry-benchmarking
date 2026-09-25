"""Delta storage adapters for local paths and managed catalog tables."""

from nz_industry_benchmarking.storage.delta import (
    CatalogDeltaStorage,
    DeltaStorage,
    LocalDeltaStorage,
)
from nz_industry_benchmarking.storage.targets import (
    CatalogTableTarget,
    LocalPathTarget,
)

__all__ = [
    "CatalogDeltaStorage",
    "CatalogTableTarget",
    "DeltaStorage",
    "LocalDeltaStorage",
    "LocalPathTarget",
]
