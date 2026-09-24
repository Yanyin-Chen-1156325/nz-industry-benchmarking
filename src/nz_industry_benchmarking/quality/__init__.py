"""Phase 6 data-quality assessment for the Silver AES dataset."""

from nz_industry_benchmarking.quality.evaluator import assess_silver_quality
from nz_industry_benchmarking.quality.models import QualityCheckResult, QualityReport

__all__ = ["QualityCheckResult", "QualityReport", "assess_silver_quality"]
