from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_report_service
from app.schemas.report_schema import (
    BreakdownItem,
    ReportFilter,
    ReportSummary,
    SalesPerformanceItem,
    TrendFilter,
    VisitTrendPoint,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Report"])

@router.get("/summary", response_model=ReportSummary)
def report_summary(
    criteria: Annotated[ReportFilter, Query()],
    service: ReportService = Depends(get_report_service),
):
    return service.summary(criteria)

@router.get("/visit-trend", response_model=list[VisitTrendPoint])
def report_visit_trend(
    criteria: Annotated[TrendFilter, Query()],
    service: ReportService = Depends(get_report_service),
):
    return service.visit_trend(criteria)

@router.get("/category", response_model=list[BreakdownItem])
def report_category(
    criteria: Annotated[ReportFilter, Query()],
    service: ReportService = Depends(get_report_service),
):
    return service.by_category(criteria)

@router.get("/source", response_model=list[BreakdownItem])
def report_source(
    criteria: Annotated[ReportFilter, Query()],
    service: ReportService = Depends(get_report_service),
):
    return service.by_source(criteria)

@router.get("/sales-performance", response_model=list[SalesPerformanceItem])
def report_sales_performance(
    criteria: Annotated[ReportFilter, Query()],
    service: ReportService = Depends(get_report_service),
):
    return service.sales_performance(criteria)
