"""Checks for the Phase 2 project foundation."""

import sys

import nz_industry_benchmarking


def test_supported_python_version() -> None:
    """The project requires Python 3.11 or newer."""
    assert sys.version_info >= (3, 11)


def test_package_exposes_version() -> None:
    """The package version is available after a source-layout import."""
    assert nz_industry_benchmarking.__version__ == "0.1.0"
