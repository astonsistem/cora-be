import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer_visits import CustomerVisits
from app.models.users import UserRole, Users
from app.schemas.customer_visit_schema import CustomerVisitCreate, CustomerVisitUpdate
from app.services import customer_service

def _scoped(query, current_user: Users):
    own = CustomerVisits.user_id == current_user.user_id
    if current_user.user_role == UserRole.sales:
        return query.where(own)

    query = query.join(Users, CustomerVisits.user_id == Users.user_id)
    if current_user.user_role == UserRole.branch_manager:
        in_scope = (
            Users.branch_id == current_user.branch_id
            if current_user.branch_id is not None
            else None
        )
    else:
        in_scope = (
            Users.company_id == current_user.company_id
            if current_user.company_id is not None
            else None
        )
    if in_scope is None:
        return query.where(own)
    return query.where(or_(own, and_(Users.user_role == UserRole.sales, in_scope)))


def _in_period(query, date_from: date | None, date_to: date | None):
    if date_from:
        query = query.where(CustomerVisits.posted_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(CustomerVisits.posted_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return query

def _filtered(
    current_user: Users,
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    query = _scoped(select(CustomerVisits), current_user)
    if user_id:
        query = query.where(CustomerVisits.user_id == user_id)
    return _in_period(query, date_from, date_to)

def get_all(
    db: Session,
    current_user: Users,
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CustomerVisits]:
    query = _filtered(current_user, user_id, date_from, date_to).order_by(CustomerVisits.posted_at.desc())
    return list(db.scalars(query.offset(skip).limit(limit)))

def count_all(
    db: Session,
    current_user: Users,
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> int:
    subquery = _filtered(current_user, user_id, date_from, date_to).subquery()
    return db.scalar(select(func.count()).select_from(subquery)) or 0

def get_summary(
    db: Session,
    current_user: Users,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    query = _scoped(
        select(
            func.count(CustomerVisits.visit_id),
            func.count(distinct(CustomerVisits.phone)),
        ).select_from(CustomerVisits),
        current_user,
    )
    total_visits, total_customers = db.execute(_in_period(query, date_from, date_to)).one()
    return {"total_visits": total_visits, "total_customers": total_customers}

def get_by_id(db: Session, visit_id: uuid.UUID) -> CustomerVisits | None:
    return db.get(CustomerVisits, visit_id)

def create_visit(db: Session, data: CustomerVisitCreate, user: Users) -> CustomerVisits:
    if data.customer_id:
        customer = customer_service.get_for_user(db, user, data.customer_id)
        if customer is None:
            raise ValueError("Customer tidak ditemukan di Master Customer")
    else:
        customer = customer_service.ensure_customer(
            db, user, data.customer_name, data.phone, data.category_id, data.branch_id
        )

    values = data.model_dump(exclude={"customer_id", "branch_id"})
    values.update(customer_id=customer.customer_id, customer_name=customer.name, phone=customer.phone or "")
    if customer.asis_partner_id:
        values.update(
            is_posted_to_asis=True,
            posted_to_asis_at=customer.posted_at,
            asis_partner_id=customer.asis_partner_id,
        )
    visit = CustomerVisits(**values, user_id=user.user_id)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit

def update_visit(db: Session, visit: CustomerVisits, data: CustomerVisitUpdate) -> CustomerVisits:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(visit, key, value)
    db.commit()
    db.refresh(visit)
    return visit

def delete_visit(db: Session, visit: CustomerVisits) -> None:
    db.delete(visit)
    db.commit()
