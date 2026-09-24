"""FastAPI routes over the framework-independent analytics service."""

from __future__ import annotations

import logging
import signal
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nz_industry_benchmarking.api.config import ApiConfig
from nz_industry_benchmarking.api.errors import (
    AnalyticalStorageError,
    NoMatchingDataError,
)
from nz_industry_benchmarking.api.models import (
    AggregationLevel,
    BenchmarkResponse,
    ChangeMetricId,
    ErrorContent,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    IndustryListResponse,
    IndustryPerformanceResponse,
    IndustryTrendResponse,
    MetricId,
    RankingType,
)
from nz_industry_benchmarking.api.repository import (
    AnalyticsRepository,
    SparkGoldRepository,
)
from nz_industry_benchmarking.api.service import AnalyticsService
from nz_industry_benchmarking.bronze.spark import create_spark_session

LOGGER = logging.getLogger("nz_industry_benchmarking.api")
ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "No matching analytical data"},
    422: {"model": ErrorResponse, "description": "Invalid request"},
    503: {"model": ErrorResponse, "description": "Analytical storage unavailable"},
}
IndustryCode = Annotated[
    str,
    Path(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9]+$"),
]
Year = Annotated[int, Query(ge=1900, le=2100)]


def create_app(
    repository: AnalyticsRepository | None = None,
    *,
    config: ApiConfig | None = None,
) -> FastAPI:
    """Create an application; injected repositories keep HTTP tests Spark-free."""
    settings = config or ApiConfig.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        spark = None
        if repository is None:
            # PySpark installs its own SIGINT handler on the main thread. Restore
            # Uvicorn's handler so Ctrl+C follows the ASGI shutdown lifecycle.
            main_thread = threading.current_thread() is threading.main_thread()
            previous_sigint = signal.getsignal(signal.SIGINT) if main_thread else None
            try:
                spark = create_spark_session(
                    master=settings.benchmark.spark_master,
                    app_name="nz-industry-benchmarking-api",
                )
            finally:
                if main_thread and previous_sigint is not None:
                    signal.signal(signal.SIGINT, previous_sigint)
            spark.sparkContext.setLogLevel(settings.benchmark.spark_log_level)
            app.state.analytics_repository = SparkGoldRepository(
                spark, settings.benchmark
            )
        else:
            app.state.analytics_repository = repository
        try:
            yield
        finally:
            if spark is not None:
                spark.stop()

    application = FastAPI(
        title="NZ Industry Benchmarking API",
        version="0.1.0",
        description=(
            "Read-only delivery of approved Stats NZ AES Gold metrics and "
            "industry benchmark rankings."
        ),
        lifespan=lifespan,
    )
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET"],
            allow_headers=["Accept", "Content-Type"],
        )
    _register_error_handlers(application)

    @application.get(
        "/api/health", response_model=HealthResponse, tags=["operations"]
    )
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get(
        "/api/industries",
        response_model=IndustryListResponse,
        responses=ERROR_RESPONSES,
        tags=["industries"],
    )
    def industries(
        request: Request,
        year: Year | None = None,
        aggregation_level: Annotated[AggregationLevel | None, Query()] = None,
    ) -> IndustryListResponse:
        return _service(request).list_industries(
            year=year, aggregation_level=aggregation_level
        )

    @application.get(
        "/api/industries/{industry}/performance",
        response_model=IndustryPerformanceResponse,
        responses=ERROR_RESPONSES,
        tags=["industries"],
    )
    def performance(
        request: Request,
        industry: IndustryCode,
        year: Year,
        aggregation_level: Annotated[AggregationLevel, Query()],
    ) -> IndustryPerformanceResponse:
        return _service(request).get_performance(
            industry_code=industry,
            year=year,
            aggregation_level=aggregation_level,
        )

    @application.get(
        "/api/industries/{industry}/trend",
        response_model=IndustryTrendResponse,
        responses=ERROR_RESPONSES,
        tags=["industries"],
    )
    def trend(
        request: Request,
        industry: IndustryCode,
        metric_id: Annotated[MetricId, Query()],
        aggregation_level: Annotated[AggregationLevel, Query()],
        start_year: Year | None = None,
        end_year: Year | None = None,
    ) -> IndustryTrendResponse:
        try:
            return _service(request).get_trend(
                industry_code=industry,
                metric_id=metric_id,
                aggregation_level=aggregation_level,
                start_year=start_year,
                end_year=end_year,
            )
        except ValueError as error:
            return _invalid_request(str(error))

    @application.get(
        "/api/benchmarks",
        response_model=BenchmarkResponse,
        responses=ERROR_RESPONSES,
        tags=["benchmarks"],
    )
    def benchmarks(
        request: Request,
        year: Year,
        metric_id: Annotated[ChangeMetricId, Query()],
        aggregation_level: Annotated[AggregationLevel, Query()],
        ranking_type: Annotated[RankingType, Query()],
        top_n: Annotated[int, Query(ge=1, le=100)] = 10,
    ) -> BenchmarkResponse:
        return _service(request).get_benchmarks(
            year=year,
            metric_id=metric_id,
            aggregation_level=aggregation_level,
            ranking_type=ranking_type,
            top_n=top_n,
        )

    return application


def _service(request: Request) -> AnalyticsService:
    return AnalyticsService(request.app.state.analytics_repository)


def _register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in item["loc"]),
                message=item["msg"],
            )
            for item in error.errors()
        ]
        return _error_response(
            status_code=422,
            code="INVALID_REQUEST",
            message="Request validation failed.",
            details=details,
        )

    @application.exception_handler(NoMatchingDataError)
    async def no_data(request: Request, error: NoMatchingDataError) -> JSONResponse:
        del request
        return _error_response(
            status_code=404,
            code="NO_MATCHING_DATA",
            message=str(error),
        )

    @application.exception_handler(AnalyticalStorageError)
    async def unavailable(
        request: Request, error: AnalyticalStorageError
    ) -> JSONResponse:
        del request
        LOGGER.exception("analytical_storage_unavailable", exc_info=error)
        return _error_response(
            status_code=503,
            code="ANALYTICAL_STORAGE_UNAVAILABLE",
            message="Analytical storage is unavailable.",
        )

    @application.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        del request
        LOGGER.exception("unhandled_api_error", exc_info=error)
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error.",
        )


def _invalid_request(message: str) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="INVALID_REQUEST",
        message=message,
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorContent(code=code, message=message, details=details or [])
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


app = create_app()
