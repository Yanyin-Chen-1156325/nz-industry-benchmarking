"""Configuration for revision processing and audit reports."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nz_industry_benchmarking.incremental.config import IncrementalConfig

DEFAULT_REVISION_REPORT_DIR = Path("data/revisions")


@dataclass(frozen=True, slots=True)
class RevisionConfig:
    """Existing pipeline configuration plus the revision audit location."""

    pipeline: IncrementalConfig
    report_dir: Path = DEFAULT_REVISION_REPORT_DIR

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> RevisionConfig:
        values = os.environ if environ is None else environ
        return cls(
            pipeline=IncrementalConfig.from_environment(values),
            report_dir=Path(
                values.get("REVISION_REPORT_DIR", DEFAULT_REVISION_REPORT_DIR)
            ),
        )
