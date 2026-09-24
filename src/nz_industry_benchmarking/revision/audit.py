"""Atomic per-artifact revision report persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from nz_industry_benchmarking.revision.models import RevisionReport


def report_path(report_dir: Path, source_sha256: str) -> Path:
    return report_dir / f"{source_sha256}.json"


def read_report(path: Path) -> RevisionReport | None:
    if not path.is_file():
        return None
    return RevisionReport.from_dict(json.loads(path.read_text(encoding="utf-8")))


def write_report(path: Path, report: RevisionReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(report.to_dict(), temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
