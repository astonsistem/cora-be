import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ForbiddenError
from app.models.customer_visits import CustomerVisits
from app.models.users import UserRole, Users
from app.schemas.customer_visit_schema import CustomerVisitCreate
from app.services.base_service import CrudService
from app.services.customer_service import CustomerService

class CustomerVisitService(CrudService[CustomerVisits]):
    model = CustomerVisits
    label = "Customer visit"
    invalid_reference_message = "Invalid source or category reference"

    def __init__(self, db: Session, current_user: Users):
        super().__init__(db)
        self.user = current_user
        self.customers = CustomerService(db, current_user)

    def get_or_404(self, obj_id) -> CustomerVisits:
        visit = super().get_or_404(obj_id)
        if self.user.user_role == UserRole.sales and visit.user_id != self.user.user_id:
            raise ForbiddenError("You can only access your own visits")
        return visit

    def _scope(self, query):
        own = CustomerVisits.user_id == self.user.user_id
        if self.user.user_role == UserRole.sales:
            return query.where(own)

        query = query.join(Users, CustomerVisits.user_id == Users.user_id)
        if self.user.user_role == UserRole.branch_manager:
            visible_roles = [UserRole.sales]
            in_scope = (
                Users.branch_id == self.user.branch_id
                if self.user.branch_id is not None
                else None
            )
        else:
            visible_roles = [UserRole.sales, UserRole.branch_manager]
            in_scope = (
                Users.company_id == self.user.company_id
                if self.user.company_id is not None
                else None
            )
        if in_scope is None:
            return query.where(own)
        return query.where(or_(own, and_(Users.user_role.in_(visible_roles), in_scope)))

    @staticmethod
    def _in_period(query, date_from: date | None, date_to: date | None):
        if date_from:
            query = query.where(CustomerVisits.posted_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.where(
                CustomerVisits.posted_at < datetime.combine(date_to + timedelta(days=1), time.min)
            )
        return query

    def _filtered(
        self,
        user_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        query = self._scope(select(CustomerVisits))
        if user_id:
            query = query.where(CustomerVisits.user_id == user_id)
        return self._in_period(query, date_from, date_to)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CustomerVisits]:
        query = self._filtered(user_id, date_from, date_to).order_by(CustomerVisits.posted_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_all(
        self,
        user_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        subquery = self._filtered(user_id, date_from, date_to).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def get_summary(self, date_from: date | None = None, date_to: date | None = None) -> dict:
        query = self._scope(
            select(
                func.count(CustomerVisits.visit_id),
                func.count(distinct(CustomerVisits.phone)),
            ).select_from(CustomerVisits)
        )
        total_visits, total_customers = self.db.execute(self._in_period(query, date_from, date_to)).one()
        return {"total_visits": total_visits, "total_customers": total_customers}

    def _build(self, data: CustomerVisitCreate) -> CustomerVisits:
        if data.customer_id:
            customer = self.customers.get_by_id(data.customer_id)
            if customer is None:
                raise BadRequestError("Customer tidak ditemukan di Master Customer")
        else:
            customer = self.customers.ensure_customer(
                data.customer_name, data.phone, data.category_id, data.branch_id
            )

        values = data.model_dump(exclude={"customer_id", "branch_id"})
        values.update(customer_id=customer.customer_id, customer_name=customer.name, phone=customer.phone or "")
        if customer.is_posted:
            values.update(
                is_posted_to_asis=True,
                posted_to_asis_at=customer.posted_at,
                asis_partner_id=customer.asis_partner_id,
            )
        return CustomerVisits(**values, user_id=self.user.user_id)
