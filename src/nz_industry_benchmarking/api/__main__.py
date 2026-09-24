"""Run the Phase 12 API with Uvicorn."""

import uvicorn

from nz_industry_benchmarking.api.config import ApiConfig


def main() -> None:
    """Start one local API process from environment configuration."""
    config = ApiConfig.from_environment()
    uvicorn.run(
        "nz_industry_benchmarking.api.app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
