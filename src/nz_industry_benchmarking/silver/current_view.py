"""Release-aware selection of one current Bronze observation per AES grain."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from nz_industry_benchmarking.silver.errors import SilverSourceError

OBSERVATION_KEY = (
    "Year",
    "Industry_aggregation_NZSIOC",
    "Industry_code_NZSIOC",
    "Variable_code",
)


def select_current_bronze_view(bronze: DataFrame) -> DataFrame:
    """Select the greatest unambiguous dataset year for each observation."""
    maximum_years = bronze.groupBy(*OBSERVATION_KEY).agg(
        F.max("dataset_year").alias("_current_dataset_year")
    )
    candidates = bronze.join(maximum_years, list(OBSERVATION_KEY), "inner").where(
        F.col("dataset_year") == F.col("_current_dataset_year")
    )
    ambiguous = (
        candidates.groupBy(*OBSERVATION_KEY)
        .agg(F.countDistinct("ingestion_id").alias("_release_count"))
        .where(F.col("_release_count") > 1)
        .count()
    )
    if ambiguous:
        raise SilverSourceError(
            "Current-view release precedence is ambiguous for "
            f"{ambiguous} observation(s): multiple artifacts share the greatest "
            "dataset_year. Phase 10 does not order dataset_version strings."
        )
    return candidates.select(*bronze.columns)
