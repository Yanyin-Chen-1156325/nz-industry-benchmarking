"""Validated identities for the two supported Delta persistence boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class LocalPathTarget:
    """A local filesystem location containing a Delta table."""

    path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("Local Delta path must be a pathlib.Path.")

    @property
    def identifier(self) -> str:
        """Return the normalized value used in existing result contracts."""
        return self.path.resolve().as_posix()

    @property
    def delta_uri(self) -> str:
        """Return the local path as a URI accepted by Spark and Delta Lake."""
        return self.path.resolve().as_uri()


@dataclass(frozen=True, slots=True)
class CatalogTableTarget:
    """A three-part Unity Catalog managed-table identity."""

    catalog: str
    schema: str
    table: str

    def __post_init__(self) -> None:
        for field_name in ("catalog", "schema", "table"):
            value = getattr(self, field_name)
            if not _IDENTIFIER.fullmatch(value):
                raise ValueError(
                    f"Invalid {field_name} identifier {value!r}; use letters, "
                    "numbers, and underscores, starting with a letter or underscore."
                )

    @property
    def identifier(self) -> str:
        """Return the fully qualified managed-table name."""
        return f"{self.catalog}.{self.schema}.{self.table}"
