import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.models.users import UserRole
from app.schemas.query_params import PeriodParams

class ReportFilter(PeriodParams):
    branch_id: uuid.UUID | None = None

class TrendFilter(ReportFilter):
    interval: Literal["day", "week", "month"] | None = "day"

    @property
    def bucket(self) -> str:
        return self.interval or "day"

class ReportSummary(BaseModel):
    total_visits: int
    total_customers: int
    active_users: int
    posted_to_asis: int
    not_posted_to_asis: int

class VisitTrendPoint(BaseModel):
    period: date
    total_visits: int
    total_customers: int

class BreakdownItem(BaseModel):
    id: uuid.UUID | None = None
    name: str
    total_visits: int
    total_customers: int
    percentage: float

class SalesPerformanceItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    role: UserRole
    branch_id: uuid.UUID | None = None
    branch_name: str | None = None
    total_visits: int
    total_customers: int
    posted_to_asis: int
    last_visit_at: datetime | None = None
