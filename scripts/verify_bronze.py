"""Print factual checks for the implemented local Bronze Delta table."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from nz_industry_benchmarking.bronze.config import BronzeConfig
from nz_industry_benchmarking.bronze.schema import BRONZE_METADATA_COLUMNS
from nz_industry_benchmarking.bronze.spark import create_spark_session
from nz_industry_benchmarking.ingestion.models import EXPECTED_COLUMNS


def main() -> None:
    """Read Bronze and report schema, fidelity, and lineage checks."""
    config = BronzeConfig.from_environment()
    spark = create_spark_session(app_name="bronze-actual-verification")
    spark.sparkContext.setLogLevel("ERROR")
    try:
        dataframe = spark.read.format("delta").load(
            config.table_path.resolve().as_uri()
        )
        metadata_columns = BRONZE_METADATA_COLUMNS[:-1]
        metadata = (
            dataframe.select(*metadata_columns).distinct().first().asDict()
        )
        result = {
            "row_count": dataframe.count(),
            "columns_match": dataframe.columns
            == [*EXPECTED_COLUMNS, *BRONZE_METADATA_COLUMNS],
            "source_column_types": {
                column: dataframe.schema[column].dataType.simpleString()
                for column in EXPECTED_COLUMNS
            },
            "C_count": dataframe.where(F.col("Value") == "C").count(),
            "S_count": dataframe.where(F.col("Value") == "S").count(),
            "metadata_distinct_records": dataframe.select(
                *metadata_columns
            ).distinct().count(),
            "metadata": metadata,
        }
        print(json.dumps(result, default=str, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
