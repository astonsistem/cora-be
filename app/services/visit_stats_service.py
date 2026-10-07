import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.branches import Branches
from app.models.companies import Companies
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers
from app.models.users import Users
from app.schemas.query_params import PeriodParams
from app.services.visit_expressions import VISIT_BRANCH
from app.services.visit_period import VisitPeriod

class VisitCountFilter(PeriodParams):
    company_id: uuid.UUID | None = None
    asis_company_id: str | None = None
    branch_id: uuid.UUID | None = None
    asis_branch_id: str | None = None

    @property
    def has_location(self) -> bool:
        return any((self.company_id, self.asis_company_id, self.branch_id, self.asis_branch_id))

class VisitStatsService:
    def __init__(self, db: Session):
        self.db = db

    def count(self, criteria: VisitCountFilter) -> int:
        criteria.validate_period()
        self._ensure_references_exist(criteria)
        query = (
            select(func.count(CustomerVisits.visit_id))
            .select_from(CustomerVisits)
            .outerjoin(Customers, CustomerVisits.customer_id == Customers.customer_id)
            .outerjoin(Users, CustomerVisits.user_id == Users.user_id)
        )
        query = VisitPeriod(criteria.date_from, criteria.date_to).apply(query)
        if criteria.has_location:
            query = query.where(VISIT_BRANCH.in_(self._branch_ids(criteria)))
        return self.db.scalar(query) or 0

    def _ensure_references_exist(self, criteria: VisitCountFilter) -> None:
        self._ensure_exists(Branches.branch_id, criteria.branch_id, "Branch")
        self._ensure_exists(Branches.asis_branch_id, criteria.asis_branch_id, "Branch")
        self._ensure_exists(Companies.company_id, criteria.company_id, "Company")
        self._ensure_exists(Companies.asis_company_id, criteria.asis_company_id, "Company")

    def _ensure_exists(self, column, value, label: str) -> None:
        if value and self.db.scalar(select(column).where(column == value).limit(1)) is None:
            raise NotFoundError(f"{label} not found")

    def _branch_ids(self, criteria: VisitCountFilter):
        query = select(Branches.branch_id).outerjoin(Companies, Branches.company_id == Companies.company_id)
        for column, value in (
            (Branches.branch_id, criteria.branch_id),
            (Branches.asis_branch_id, criteria.asis_branch_id),
            (Companies.company_id, criteria.company_id),
            (Companies.asis_company_id, criteria.asis_company_id),
        ):
            if value:
                query = query.where(column == value)
        return query
