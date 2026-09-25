"""Environment-specific Delta I/O kept below shared transformations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from nz_industry_benchmarking.storage.targets import (
    CatalogTableTarget,
    LocalPathTarget,
)

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


class DeltaStorage(Protocol):
    """Minimal storage behavior required by the existing pipeline writers."""

    @property
    def identifier(self) -> str: ...

    def exists(self) -> bool: ...

    def read(self) -> DataFrame: ...

    def write(
        self,
        dataframe: DataFrame,
        *,
        mode: str,
        options: Mapping[str, object] | None = None,
    ) -> None: ...


class LocalDeltaStorage:
    """Read and write a Delta table at a local filesystem path."""

    def __init__(self, spark: SparkSession, target: LocalPathTarget) -> None:
        self._spark = spark
        self._target = target

    @property
    def identifier(self) -> str:
        return self._target.identifier

    def exists(self) -> bool:
        # Keep the DeltaTable dependency local to the path adapter. Catalog
        # execution never imports or calls this path-oriented check.
        from delta.tables import DeltaTable

        return DeltaTable.isDeltaTable(self._spark, self._target.delta_uri)

    def read(self) -> DataFrame:
        return self._spark.read.format("delta").load(self._target.delta_uri)

    def write(
        self,
        dataframe: DataFrame,
        *,
        mode: str,
        options: Mapping[str, object] | None = None,
    ) -> None:
        self._target.path.resolve().parent.mkdir(parents=True, exist_ok=True)
        writer = dataframe.write.format("delta").mode(mode)
        for name, value in (options or {}).items():
            writer = writer.option(name, value)
        writer.save(self._target.delta_uri)


class CatalogDeltaStorage:
    """Read and write a Unity Catalog managed Delta table."""

    def __init__(self, spark: SparkSession, target: CatalogTableTarget) -> None:
        self._spark = spark
        self._target = target

    @property
    def identifier(self) -> str:
        return self._target.identifier

    def exists(self) -> bool:
        return self._spark.catalog.tableExists(self._target.identifier)

    def read(self) -> DataFrame:
        return self._spark.table(self._target.identifier)

    def write(
        self,
        dataframe: DataFrame,
        *,
        mode: str,
        options: Mapping[str, object] | None = None,
    ) -> None:
        writer = dataframe.write.format("delta").mode(mode)
        for name, value in (options or {}).items():
            writer = writer.option(name, value)
        writer.saveAsTable(self._target.identifier)
