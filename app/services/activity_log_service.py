import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.exceptions import ForbiddenError
from app.models.activity_log import ActivityLogs
from app.models.branches import Branches
from app.models.companies import Companies
from app.models.users import Users

MAX_PAGE_SIZE = 10000

SORT_COLUMNS = {
    "created_at": ActivityLogs.created_at,
    "user_name": ActivityLogs.user_name,
    "action": ActivityLogs.action,
    "module": ActivityLogs.module,
    "company_name": Companies.company_name,
    "branch_name": Branches.branch_name,
}


class ActivityLogService:
    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.user = current_user

    def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        sort_by: str | None = None,
        sort_order: str | None = None,
        archived: bool = False,
        **filters,
    ) -> list[ActivityLogs]:
        query = self._filtered(select(ActivityLogs), archived=archived, **filters).options(
            contains_eager(ActivityLogs.company), contains_eager(ActivityLogs.branch)
        )
        query = query.order_by(*self._ordering(sort_by, sort_order))
        return list(self.db.scalars(query.offset(max(skip, 0)).limit(min(max(limit, 1), MAX_PAGE_SIZE))))

    def count_all(self, archived: bool = False, **filters) -> int:
        subquery = self._filtered(select(ActivityLogs.log_id), archived=archived, **filters).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def filter_options(self) -> dict:
        branches = select(Branches).where(Branches.deleted_at.is_(None)).order_by(Branches.branch_name)
        if self.user.is_superadmin:
            companies = select(Companies).where(Companies.deleted_at.is_(None)).order_by(Companies.company_name)
            return {
                "companies": [
                    {"company_id": item.company_id, "name": item.company_name}
                    for item in self.db.scalars(companies)
                ],
                "branches": self._branch_options(self.db.scalars(branches)),
            }
        branches = branches.where(Branches.company_id == self._company_id())
        return {"companies": [], "branches": self._branch_options(self.db.scalars(branches))}

    def _company_id(self) -> uuid.UUID:
        if self.user.company_id is None:
            raise ForbiddenError("Akun Anda belum terhubung ke company")
        return self.user.company_id

    @staticmethod
    def _branch_options(branches) -> list[dict]:
        return [
            {"branch_id": item.branch_id, "company_id": item.company_id, "name": item.branch_name}
            for item in branches
        ]

    def _filtered(
        self,
        query,
        archived: bool = False,
        q: str | None = None,
        action: str | None = None,
        module: str | None = None,
        company_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        query = query.outerjoin(Companies, Companies.company_id == ActivityLogs.company_id).outerjoin(
            Branches, Branches.branch_id == ActivityLogs.branch_id
        )
        query = query.where(ActivityLogs.archived_at.is_not(None) if archived else ActivityLogs.archived_at.is_(None))
        if self.user.is_superadmin:
            if company_id:
                query = query.where(ActivityLogs.company_id == company_id)
        else:
            query = query.where(ActivityLogs.company_id == self._company_id())
        if action:
            query = query.where(ActivityLogs.action == action)
        if module:
            query = query.where(ActivityLogs.module == module)
        if branch_id:
            query = query.where(ActivityLogs.branch_id == branch_id)
        if date_from:
            query = query.where(ActivityLogs.created_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.where(ActivityLogs.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            query = query.where(
                or_(ActivityLogs.user_name.ilike(pattern), ActivityLogs.description.ilike(pattern))
            )
        return query

    @staticmethod
    def _ordering(sort_by: str | None, sort_order: str | None) -> list:
        column = SORT_COLUMNS.get(sort_by or "")
        if column is None:
            return [ActivityLogs.created_at.desc()]
        ordered = column.desc() if sort_order == "desc" else column.asc()
        return [ordered, ActivityLogs.created_at.desc()]
