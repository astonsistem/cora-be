import uuid
from datetime import date, timedelta

from sqlalchemy import and_, desc, distinct, func, literal_column, or_, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.branches import Branches
from app.models.category import Category
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers
from app.models.sources import Sources
from app.models.users import UserRole, Users
from app.schemas.query_params import PeriodParams
from app.schemas.report_schema import ReportFilter, TrendFilter
from app.services.visit_expressions import CUSTOMER_KEY, VISIT_BRANCH
from app.services.visit_period import VisitPeriod
from app.services.visit_scope import VisitScope

class ReportService:
    MAX_FILLED_PERIODS = 3660

    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.user = current_user
        self.scope = VisitScope(current_user)

    def summary(self, criteria: ReportFilter) -> dict:
        query = self._visits(
            criteria,
            func.count(CustomerVisits.visit_id),
            func.count(distinct(CUSTOMER_KEY)),
            func.count(distinct(CustomerVisits.user_id)),
            func.count(CustomerVisits.visit_id).filter(CustomerVisits.is_posted_to_asis.is_(True)),
        )
        total_visits, total_customers, active_users, posted = self.db.execute(query).one()
        return {
            "total_visits": total_visits,
            "total_customers": total_customers,
            "active_users": active_users,
            "posted_to_asis": posted,
            "not_posted_to_asis": total_visits - posted,
        }

    def visit_trend(self, criteria: TrendFilter) -> list[dict]:
        bucket = func.date_trunc(literal_column(f"'{criteria.bucket}'"), CustomerVisits.posted_at)
        query = (
            self._visits(criteria, bucket, func.count(CustomerVisits.visit_id), func.count(distinct(CUSTOMER_KEY)))
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = {row[0].date(): (row[1], row[2]) for row in self.db.execute(query)}
        return self._fill_periods(rows, criteria)

    def by_category(self, criteria: ReportFilter) -> list[dict]:
        return self._breakdown(
            criteria, Category, Category.category_id, Category.name, CustomerVisits.category_id, "Tanpa kategori"
        )

    def by_source(self, criteria: ReportFilter) -> list[dict]:
        return self._breakdown(
            criteria, Sources, Sources.source_id, Sources.name, CustomerVisits.source_id, "Tanpa sumber"
        )

    def sales_performance(self, criteria: ReportFilter) -> list[dict]:
        self._validate(criteria)
        visits_count = func.count(CustomerVisits.visit_id)
        joined_visits = and_(CustomerVisits.user_id == Users.user_id, *VisitPeriod(criteria.date_from, criteria.date_to).conditions())
        query = (
            select(
                Users.user_id,
                Users.first_name,
                Users.last_name,
                Users.user_role,
                Users.branch_id,
                Branches.branch_name,
                visits_count,
                func.count(distinct(CUSTOMER_KEY)),
                visits_count.filter(CustomerVisits.is_posted_to_asis.is_(True)),
                func.max(CustomerVisits.posted_at),
            )
            .select_from(Users)
            .outerjoin(CustomerVisits, joined_visits)
            .outerjoin(Branches, Users.branch_id == Branches.branch_id)
            .where(self.scope.user_condition())
            .group_by(Users.user_id, Branches.branch_id)
            .order_by(desc(visits_count), Users.first_name, Users.last_name)
        )
        if not criteria.user_id:
            query = query.where(
                or_(
                    CustomerVisits.visit_id.is_not(None),
                    and_(Users.user_role == UserRole.sales, Users.is_active.is_(True)),
                )
            )
        if criteria.branch_id:
            query = query.where(Users.branch_id == criteria.branch_id)
        query = self._filter_users(query, criteria)
        return [
            {
                "user_id": user_id,
                "full_name": f"{first_name} {last_name}".strip(),
                "role": role,
                "branch_id": branch_id,
                "branch_name": branch_name,
                "total_visits": total_visits,
                "total_customers": total_customers,
                "posted_to_asis": posted,
                "last_visit_at": last_visit_at,
            }
            for (user_id, first_name, last_name, role, branch_id, branch_name,
                 total_visits, total_customers, posted, last_visit_at) in self.db.execute(query)
        ]

    def sales_performance_by_id(self, user_id: uuid.UUID, period: PeriodParams) -> dict:
        criteria = ReportFilter(date_from=period.date_from, date_to=period.date_to, user_id=user_id)
        return self.sales_performance(criteria)[0]

    def _visits(self, criteria: ReportFilter, *columns):
        self._validate(criteria)
        query = (
            select(*columns)
            .select_from(CustomerVisits)
            .outerjoin(Customers, CustomerVisits.customer_id == Customers.customer_id)
        )
        query = self.scope.apply(query)
        query = VisitPeriod(criteria.date_from, criteria.date_to).apply(query)
        if criteria.branch_id:
            query = query.where(VISIT_BRANCH == criteria.branch_id)
        return self._filter_users(query, criteria)

    @staticmethod
    def _filter_users(query, criteria: ReportFilter):
        if criteria.user_id:
            query = query.where(Users.user_id == criteria.user_id)
        if criteria.user_role:
            query = query.where(Users.user_role == criteria.user_role)
        return query

    def _validate(self, criteria: ReportFilter) -> None:
        criteria.validate_period()
        self._ensure_branch_exists(criteria)
        self._ensure_user_visible(criteria)

    def _ensure_branch_exists(self, criteria: ReportFilter) -> None:
        if criteria.branch_id and self.db.scalar(
            select(Branches.branch_id).where(Branches.branch_id == criteria.branch_id).limit(1)
        ) is None:
            raise NotFoundError("Branch not found")

    def _ensure_user_visible(self, criteria: ReportFilter) -> None:
        if criteria.user_id and self.db.scalar(
            select(Users.user_id).where(Users.user_id == criteria.user_id).where(self.scope.user_condition()).limit(1)
        ) is None:
            raise NotFoundError("User not found")

    def _breakdown(self, criteria: ReportFilter, entity, id_column, name_column, foreign_key, empty_label: str) -> list[dict]:
        visits_count = func.count(CustomerVisits.visit_id)
        query = (
            self._visits(criteria, id_column, name_column, visits_count, func.count(distinct(CUSTOMER_KEY)))
            .outerjoin(entity, foreign_key == id_column)
            .group_by(id_column, name_column)
            .order_by(desc(visits_count), name_column)
        )
        rows = list(self.db.execute(query))
        total = sum(row[2] for row in rows)
        return [
            {
                "id": item_id,
                "name": name or empty_label,
                "total_visits": total_visits,
                "total_customers": total_customers,
                "percentage": round(total_visits * 100 / total, 1) if total else 0.0,
            }
            for item_id, name, total_visits, total_customers in rows
        ]

    def _fill_periods(self, rows: dict, criteria: TrendFilter) -> list[dict]:
        if not rows and not (criteria.date_from and criteria.date_to):
            return []
        interval = criteria.bucket
        start = self._floor(criteria.date_from or min(rows), interval)
        end = criteria.date_to or max(rows)
        if (end - start).days > self.MAX_FILLED_PERIODS:
            return [self._point(period, *rows[period]) for period in sorted(rows)]
        points = []
        cursor = start
        while cursor <= end:
            points.append(self._point(cursor, *rows.get(cursor, (0, 0))))
            cursor = self._advance(cursor, interval)
        return points

    @staticmethod
    def _point(period: date, total_visits: int, total_customers: int) -> dict:
        return {"period": period, "total_visits": total_visits, "total_customers": total_customers}

    @staticmethod
    def _floor(value: date, interval: str) -> date:
        if interval == "week":
            return value - timedelta(days=value.weekday())
        if interval == "month":
            return value.replace(day=1)
        return value

    @staticmethod
    def _advance(value: date, interval: str) -> date:
        if interval == "week":
            return value + timedelta(days=7)
        if interval == "month":
            return date(value.year + value.month // 12, value.month % 12 + 1, 1)
        return value + timedelta(days=1)
