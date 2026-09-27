"""Databricks SQL implementation of the read-only analytics repository."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from nz_industry_benchmarking.api.errors import AnalyticalStorageError
from nz_industry_benchmarking.api.records import (
    BenchmarkRecord,
    IndustryRecord,
    MetricRecord,
)
from nz_industry_benchmarking.benchmarking.models import BenchmarkRequest

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_METRIC_COLUMNS = """metric_record_id,
                year,
                industry_aggregation_nzsioc,
                industry_code_nzsioc,
                industry_name_nzsioc,
                metric_id,
                metric_name,
                metric_value,
                metric_status,
                metric_unit,
                current_input_status,
                prior_input_status,
                source_silver_record_ids,
                source_ingestion_ids,
                source_sha256s,
                gold_input_fingerprint"""


class _Cursor(Protocol):
    def execute(self, operation: str, parameters: Sequence[object]) -> None: ...

    def fetchall(self) -> Sequence[Sequence[object]]: ...

    def close(self) -> None: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DatabricksSqlConfig:
    """Connection inputs and trusted managed-table identifiers."""

    server_hostname: str
    http_path: str
    access_token: str = field(repr=False)
    catalog: str = "workspace"
    schema: str = "nz_industry_benchmarking"
    gold_table: str = "gold_industry_financial_metrics"

    def __post_init__(self) -> None:
        for name in ("server_hostname", "http_path", "access_token"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank.")
        for name in ("catalog", "schema", "gold_table"):
            value = getattr(self, name)
            if not _IDENTIFIER_PATTERN.fullmatch(value):
                raise ValueError(
                    f"{name} must be a simple SQL identifier containing only "
                    "letters, digits, and underscores, and must not start with a digit."
                )

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> DatabricksSqlConfig:
        """Load connection values without placing credentials in source code."""
        values = os.environ if environ is None else environ
        missing = [
            name
            for name in (
                "DATABRICKS_SERVER_HOSTNAME",
                "DATABRICKS_HTTP_PATH",
                "DATABRICKS_TOKEN",
            )
            if not values.get(name, "").strip()
        ]
        if missing:
            raise ValueError(
                "Missing required Databricks SQL environment variables: "
                + ", ".join(missing)
            )
        return cls(
            server_hostname=values["DATABRICKS_SERVER_HOSTNAME"],
            http_path=values["DATABRICKS_HTTP_PATH"],
            access_token=values["DATABRICKS_TOKEN"],
            catalog=values.get("DATABRICKS_CATALOG", "workspace"),
            schema=values.get("DATABRICKS_SCHEMA", "nz_industry_benchmarking"),
            gold_table=values.get(
                "DATABRICKS_GOLD_TABLE", "gold_industry_financial_metrics"
            ),
        )

    @property
    def qualified_gold_table(self) -> str:
        """Return a quoted name built only from validated configuration."""
        return ".".join(
            f"`{identifier}`"
            for identifier in (self.catalog, self.schema, self.gold_table)
        )


ConnectionFactory = Callable[[DatabricksSqlConfig], _Connection]


def _default_connection_factory(config: DatabricksSqlConfig) -> _Connection:
    from databricks import sql

    return sql.connect(
        server_hostname=config.server_hostname,
        http_path=config.http_path,
        access_token=config.access_token,
    )


class DatabricksSqlAnalyticsRepository:
    """Read the managed Gold table through a Databricks SQL endpoint."""

    def __init__(
        self,
        config: DatabricksSqlConfig,
        connection_factory: ConnectionFactory = _default_connection_factory,
    ) -> None:
        self._config = config
        self._connection_factory = connection_factory
        self._table = config.qualified_gold_table

    def list_industries(
        self, *, year: int | None, aggregation_level: str | None
    ) -> Sequence[IndustryRecord]:
        """Return distinct industries and the available years in Gold."""
        predicates: list[str] = []
        parameters: list[object] = []
        if year is not None:
            predicates.append("year = ?")
            parameters.append(year)
        if aggregation_level is not None:
            predicates.append("industry_aggregation_nzsioc = ?")
            parameters.append(aggregation_level)
        where = f"WHERE {' AND '.join(predicates)}" if predicates else ""
        operation = f"""
            SELECT DISTINCT
                industry_code_nzsioc,
                industry_name_nzsioc,
                industry_aggregation_nzsioc,
                year
            FROM {self._table}
            {where}
            ORDER BY
                industry_aggregation_nzsioc,
                industry_code_nzsioc,
                industry_name_nzsioc,
                year
        """
        rows = self._fetch_all(
            operation, parameters, "Databricks Gold industry query failed."
        )
        grouped: dict[tuple[str, str, str], set[int]] = {}
        for row in rows:
            key = (str(row[0]), str(row[1]), str(row[2]))
            grouped.setdefault(key, set()).add(int(row[3]))
        return [
            IndustryRecord(
                industry_code=code,
                industry_name=name,
                aggregation_level=level,
                available_years=tuple(sorted(years)),
            )
            for (code, name, level), years in sorted(
                grouped.items(), key=lambda item: (item[0][2], item[0][0], item[0][1])
            )
        ]

    def get_metrics(
        self, *, industry_code: str, year: int, aggregation_level: str
    ) -> Sequence[MetricRecord]:
        """Return existing Gold observations for one industry and year."""
        operation = f"""
            SELECT {_METRIC_COLUMNS}
            FROM {self._table}
            WHERE industry_code_nzsioc = ?
              AND year = ?
              AND industry_aggregation_nzsioc = ?
            ORDER BY metric_id
        """
        rows = self._fetch_all(
            operation,
            (industry_code, year, aggregation_level),
            "Databricks Gold performance query failed.",
        )
        return [_metric_record(row) for row in rows]

    def get_trend(
        self,
        *,
        industry_code: str,
        metric_id: str,
        aggregation_level: str,
        start_year: int | None,
        end_year: int | None,
    ) -> Sequence[MetricRecord]:
        """Return existing Gold observations in chronological order."""
        predicates = [
            "industry_code_nzsioc = ?",
            "metric_id = ?",
            "industry_aggregation_nzsioc = ?",
        ]
        parameters: list[object] = [
            industry_code,
            metric_id,
            aggregation_level,
        ]
        if start_year is not None:
            predicates.append("year >= ?")
            parameters.append(start_year)
        if end_year is not None:
            predicates.append("year <= ?")
            parameters.append(end_year)
        operation = f"""
            SELECT {_METRIC_COLUMNS}
            FROM {self._table}
            WHERE {" AND ".join(predicates)}
            ORDER BY year
        """
        rows = self._fetch_all(
            operation, parameters, "Databricks Gold trend query failed."
        )
        return [_metric_record(row) for row in rows]

    def get_benchmarks(self, request: BenchmarkRequest) -> Sequence[BenchmarkRecord]:
        """Return one ranking partition using the existing Phase 8 semantics."""
        value_filter, primary_order = {
            "top_increases": ("AND metric_value > 0", "metric_value DESC"),
            "top_decreases": ("AND metric_value < 0", "metric_value ASC"),
            "largest_movements": ("", "ABS(metric_value) DESC"),
        }[request.ranking_type]
        operation = f"""
            WITH eligible AS (
                SELECT *
                FROM {self._table}
                WHERE year = ?
                  AND metric_id = ?
                  AND industry_aggregation_nzsioc = ?
                  AND metric_status = ?
                  AND metric_value IS NOT NULL
                  {value_filter}
            ), ranked AS (
                SELECT
                    ? AS ranking_type,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            year,
                            metric_id,
                            industry_aggregation_nzsioc
                        ORDER BY
                            {primary_order},
                            industry_code_nzsioc ASC,
                            industry_name_nzsioc ASC,
                            metric_record_id ASC
                    ) AS rank_position,
                    year,
                    industry_aggregation_nzsioc,
                    metric_id,
                    metric_name,
                    metric_value,
                    ABS(metric_value) AS absolute_metric_value,
                    metric_status,
                    metric_unit,
                    industry_code_nzsioc,
                    industry_name_nzsioc,
                    metric_record_id,
                    source_silver_record_ids,
                    source_ingestion_ids,
                    source_sha256s,
                    gold_input_fingerprint,
                    gold_processing_timestamp
                FROM eligible
            )
            SELECT *
            FROM ranked
            WHERE rank_position <= ?
            ORDER BY rank_position
        """
        rows = self._fetch_all(
            operation,
            (
                request.year,
                request.metric_id,
                request.aggregation_level,
                "PUBLISHED",
                request.ranking_type,
                request.top_n,
            ),
            "Databricks Gold benchmark query failed.",
        )
        return [_benchmark_record(row) for row in rows]

    def _fetch_all(
        self,
        operation: str,
        parameters: Sequence[object],
        safe_error_message: str,
    ) -> Sequence[Sequence[object]]:
        try:
            with closing(self._connection_factory(self._config)) as connection:
                with closing(connection.cursor()) as cursor:
                    cursor.execute(operation, parameters)
                    return cursor.fetchall()
        except Exception:
            # Connector errors can contain endpoint or authentication details.
            raise AnalyticalStorageError(safe_error_message) from None


def _metric_record(row: Sequence[object]) -> MetricRecord:
    return MetricRecord(
        metric_record_id=str(row[0]),
        year=int(row[1]),
        aggregation_level=str(row[2]),
        industry_code=str(row[3]),
        industry_name=str(row[4]),
        metric_id=str(row[5]),
        metric_name=str(row[6]),
        metric_value=_optional_decimal(row[7]),
        metric_status=str(row[8]),
        metric_unit=str(row[9]),
        current_input_status=_optional_string(row[10]),
        prior_input_status=_optional_string(row[11]),
        source_silver_record_ids=_string_tuple(row[12]),
        source_ingestion_ids=_string_tuple(row[13]),
        source_sha256s=_string_tuple(row[14]),
        gold_input_fingerprint=str(row[15]),
    )


def _benchmark_record(row: Sequence[object]) -> BenchmarkRecord:
    return BenchmarkRecord(
        ranking_type=str(row[0]),
        rank_position=int(row[1]),
        year=int(row[2]),
        aggregation_level=str(row[3]),
        metric_id=str(row[4]),
        metric_name=str(row[5]),
        metric_value=_required_decimal(row[6]),
        absolute_metric_value=_required_decimal(row[7]),
        metric_status=str(row[8]),
        metric_unit=str(row[9]),
        industry_code=str(row[10]),
        industry_name=str(row[11]),
        metric_record_id=str(row[12]),
        source_silver_record_ids=_string_tuple(row[13]),
        source_ingestion_ids=_string_tuple(row[14]),
        source_sha256s=_string_tuple(row[15]),
        gold_input_fingerprint=str(row[16]),
        gold_processing_timestamp=_required_datetime(row[17]),
    )


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else _required_decimal(value)


def _required_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        raise TypeError("Expected a non-null decimal value.")
    return Decimal(str(value))


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise TypeError("Expected an array of strings.") from None
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        raise TypeError("Expected an array of strings.")
    return tuple(value)


def _required_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError("Expected a timestamp value.")
