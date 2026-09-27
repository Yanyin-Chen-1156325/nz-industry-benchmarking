"""Select and own the configured analytical repository lifecycle."""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Protocol

from nz_industry_benchmarking.api.config import AnalyticsBackend, ApiConfig
from nz_industry_benchmarking.api.protocols import AnalyticsRepository


class _SparkContext(Protocol):
    def setLogLevel(self, level: str) -> None: ...


class _SparkSession(Protocol):
    sparkContext: _SparkContext

    def stop(self) -> None: ...


SparkSessionFactory = Callable[..., _SparkSession]


@contextmanager
def configured_repository(
    config: ApiConfig,
    *,
    spark_session_factory: SparkSessionFactory | None = None,
) -> Iterator[AnalyticsRepository]:
    """Yield the selected repository and close only owned Spark resources."""
    if config.analytics_backend is AnalyticsBackend.DATABRICKS_SQL:
        from nz_industry_benchmarking.api.databricks_repository import (
            DatabricksSqlAnalyticsRepository,
        )

        if config.databricks_sql is None:
            raise ValueError("Databricks SQL configuration is required.")
        yield DatabricksSqlAnalyticsRepository(config.databricks_sql)
        return

    if spark_session_factory is None:
        from nz_industry_benchmarking.bronze.spark import create_spark_session

        spark_session_factory = create_spark_session

    # PySpark installs a SIGINT handler on the main thread. Restore Uvicorn's
    # handler so Ctrl+C follows the ASGI shutdown lifecycle.
    main_thread = threading.current_thread() is threading.main_thread()
    previous_sigint = signal.getsignal(signal.SIGINT) if main_thread else None
    try:
        spark = spark_session_factory(
            master=config.benchmark.spark_master,
            app_name="nz-industry-benchmarking-api",
        )
    finally:
        if main_thread and previous_sigint is not None:
            signal.signal(signal.SIGINT, previous_sigint)

    try:
        from nz_industry_benchmarking.api.repository import SparkGoldRepository

        spark.sparkContext.setLogLevel(config.benchmark.spark_log_level)
        yield SparkGoldRepository(spark, config.benchmark)
    finally:
        spark.stop()
