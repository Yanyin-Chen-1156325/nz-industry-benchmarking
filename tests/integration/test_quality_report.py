"""Integration coverage for Silver Delta quality assessment and reporting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from nz_industry_benchmarking.quality.config import QualityConfig
from nz_industry_benchmarking.quality.service import run_quality_assessment
from nz_industry_benchmarking.silver.transform import transform_bronze_to_silver


def test_quality_service_reads_silver_and_writes_report(
    spark,
    bronze_dataframe_factory,
    tmp_path: Path,
) -> None:
    silver_path = tmp_path / "silver"
    report_path = tmp_path / "reports" / "quality.json"
    timestamp = datetime(2026, 9, 24, 3, 4, 5, tzinfo=UTC)
    bronze = bronze_dataframe_factory(
        {"Value": "-1"},
        {"Industry_code_NZSIOC": "BB", "Value": "C"},
    )
    silver = transform_bronze_to_silver(
        bronze,
        input_fingerprint="QUALITY-INTEGRATION",
        processing_timestamp=timestamp,
    )
    silver.write.format("delta").save(silver_path.resolve().as_uri())

    report = run_quality_assessment(
        spark,
        QualityConfig(silver_path=silver_path, report_path=report_path),
        clock=lambda: timestamp,
    )
    stored = json.loads(report_path.read_text(encoding="utf-8"))

    assert report.overall_result == "PASS"
    assert report.rows_processed == 2
    assert stored == report.to_dict()
    assert stored["checks_executed"] == 16
