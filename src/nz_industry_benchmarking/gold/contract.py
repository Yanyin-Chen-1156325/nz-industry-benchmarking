"""Authoritative Phase 1 metric mappings used by the Gold transformation."""

from __future__ import annotations

from dataclasses import dataclass

GOLD_SCHEMA_VERSION = "aes-gold-metrics-v1"
GOLD_LOGIC_VERSION = "aes-gold-rules-v3"


@dataclass(frozen=True, slots=True)
class DirectMetricSpec:
    """Exact Silver source contract for a direct approved metric."""

    metric_id: str
    metric_name: str
    variable_code: str
    variable_name: str
    variable_category: str
    source_units: str
    metric_unit: str


@dataclass(frozen=True, slots=True)
class DerivedMetricSpec:
    """Approved year-over-year metric tied to one direct metric."""

    metric_id: str
    metric_name: str
    source_metric_id: str
    metric_unit: str


DIRECT_METRICS = (
    DirectMetricSpec(
        metric_id="M1",
        metric_name="Total income",
        variable_code="H01",
        variable_name="Total income",
        variable_category="Financial performance",
        source_units="Dollars (millions)",
        metric_unit="NZD millions",
    ),
    DirectMetricSpec(
        metric_id="M2",
        metric_name="Surplus before income tax",
        variable_code="H23",
        variable_name="Surplus before income tax",
        variable_category="Financial performance",
        source_units="Dollars (millions)",
        metric_unit="NZD millions",
    ),
    DirectMetricSpec(
        metric_id="M3",
        metric_name="Return on total assets",
        variable_code="H40",
        variable_name="Return on total assets",
        variable_category="Financial ratios",
        source_units="Percentage",
        metric_unit="Percent",
    ),
)

DERIVED_METRICS = (
    DerivedMetricSpec(
        metric_id="M4",
        metric_name="Total income year-over-year growth",
        source_metric_id="M1",
        metric_unit="Percent change",
    ),
    DerivedMetricSpec(
        metric_id="M5",
        metric_name="Surplus before income tax year-over-year change",
        source_metric_id="M2",
        metric_unit="NZD millions change",
    ),
    DerivedMetricSpec(
        metric_id="M6",
        metric_name="Return on total assets year-over-year change",
        source_metric_id="M3",
        metric_unit="Percentage points",
    ),
)

METRIC_IDS = tuple(spec.metric_id for spec in (*DIRECT_METRICS, *DERIVED_METRICS))

GOLD_STATUSES = (
    "PUBLISHED",
    "CONFIDENTIAL",
    "SUPPRESSED",
    "UNAVAILABLE",
    "INVALID_DUPLICATE",
    "INVALID_VALUE",
    "UNAVAILABLE_INPUT",
    "NOT_MEANINGFUL_BASE",
)
