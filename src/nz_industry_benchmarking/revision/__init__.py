"""Phase 10 official-release revision handling."""

from nz_industry_benchmarking.revision.config import RevisionConfig
from nz_industry_benchmarking.revision.service import run_revision_pipeline

__all__ = ["RevisionConfig", "run_revision_pipeline"]
