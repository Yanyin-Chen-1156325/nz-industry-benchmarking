"""Spark-free checks for local and managed Delta storage boundaries."""

from pathlib import Path

import pytest

from nz_industry_benchmarking.storage import (
    CatalogDeltaStorage,
    CatalogTableTarget,
    LocalPathTarget,
)


class _FakeWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def format(self, value: str):
        self.calls.append(("format", value))
        return self

    def mode(self, value: str):
        self.calls.append(("mode", value))
        return self

    def option(self, name: str, value: object):
        self.calls.append(("option", name, value))
        return self

    def saveAsTable(self, name: str) -> None:  # noqa: N802
        self.calls.append(("saveAsTable", name))


class _FakeDataFrame:
    def __init__(self) -> None:
        self.write = _FakeWriter()


class _FakeCatalog:
    def __init__(self) -> None:
        self.lookups: list[str] = []

    def tableExists(self, name: str) -> bool:  # noqa: N802
        self.lookups.append(name)
        return True


class _FakeSpark:
    def __init__(self) -> None:
        self.catalog = _FakeCatalog()
        self.table_reads: list[str] = []

    def table(self, name: str) -> str:
        self.table_reads.append(name)
        return f"frame:{name}"


def test_local_path_target_keeps_existing_resolved_path_contract(
    tmp_path: Path,
) -> None:
    target = LocalPathTarget(tmp_path / "bronze" / "aes")

    assert target.identifier == (tmp_path / "bronze" / "aes").resolve().as_posix()
    assert target.delta_uri == (tmp_path / "bronze" / "aes").resolve().as_uri()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("catalog", "bad-name"),
        ("schema", "two words"),
        ("table", "9starts_with_number"),
    ],
)
def test_catalog_target_rejects_unsafe_identifiers(field: str, value: str) -> None:
    values = {"catalog": "workspace", "schema": "analytics", "table": "bronze"}
    values[field] = value

    with pytest.raises(ValueError, match=f"Invalid {field} identifier"):
        CatalogTableTarget(**values)


def test_catalog_storage_uses_managed_table_operations() -> None:
    spark = _FakeSpark()
    dataframe = _FakeDataFrame()
    target = CatalogTableTarget("workspace", "analytics", "bronze_aes")
    storage = CatalogDeltaStorage(spark, target)

    assert storage.identifier == "workspace.analytics.bronze_aes"
    assert storage.exists() is True
    assert storage.read() == "frame:workspace.analytics.bronze_aes"
    storage.write(
        dataframe,
        mode="overwrite",
        options={"overwriteSchema": "true"},
    )

    assert spark.catalog.lookups == ["workspace.analytics.bronze_aes"]
    assert spark.table_reads == ["workspace.analytics.bronze_aes"]
    assert dataframe.write.calls == [
        ("format", "delta"),
        ("mode", "overwrite"),
        ("option", "overwriteSchema", "true"),
        ("saveAsTable", "workspace.analytics.bronze_aes"),
    ]
