"""Small Spark-session factory configured for Delta Lake."""

from __future__ import annotations

import os
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


def create_spark_session(
    *,
    master: str = "local[2]",
    app_name: str = "nz-industry-benchmarking-bronze",
) -> SparkSession:
    """Create a local-capable Spark session with Delta SQL extensions."""
    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.jars.repositories", "https://repo.maven.apache.org/maven2")
    )
    local_jars = os.environ.get("DELTA_SPARK_LOCAL_JARS")
    if local_jars:
        classpath = str(Path(local_jars).resolve() / "*")
        return (
            builder.config("spark.driver.extraClassPath", classpath)
            .config("spark.executor.extraClassPath", classpath)
            .getOrCreate()
        )
    return configure_spark_with_delta_pip(builder).getOrCreate()
