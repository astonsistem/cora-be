import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.customer_visits import CustomerVisits
from app.models.users import UserRole, Users
from app.schemas.customer_visit_schema import CustomerVisitCreate, CustomerVisitUpdate

def _scoped(query, current_user: Users):
    """Batasi query ke visit yang boleh dilihat current_user.

    sales: miliknya sendiri, branch_manager: visit sales di branch-nya,
    operasional_manager: visit sales di company-nya.
    Mengembalikan None kalau user tidak punya cakupan (branch/company kosong).
    """
    if current_user.user_role == UserRole.sales:
        return query.where(CustomerVisits.user_id == current_user.user_id)

    query = query.join(Users, CustomerVisits.user_id == Users.user_id).where(
        Users.user_role == UserRole.sales
    )
    if current_user.user_role == UserRole.branch_manager:
        if current_user.branch_id is None:
            return None
        return query.where(Users.branch_id == current_user.branch_id)

    if current_user.company_id is None:
        return None
    return query.where(Users.company_id == current_user.company_id)


def _in_period(query, date_from: date | None, date_to: date | None):
    if date_from:
        query = query.where(CustomerVisits.posted_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(CustomerVisits.posted_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return query


def get_all(
    db: Session,
    current_user: Users,
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CustomerVisits]:
    query = _scoped(select(CustomerVisits).order_by(CustomerVisits.posted_at.desc()), current_user)
    if query is None:
        return []
    if user_id:
        query = query.where(CustomerVisits.user_id == user_id)
    query = _in_period(query, date_from, date_to)
    return list(db.scalars(query.offset(skip).limit(limit)))


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
    if query is None:
        return {"total_visits": 0, "total_customers": 0}
    total_visits, total_customers = db.execute(_in_period(query, date_from, date_to)).one()
    return {"total_visits": total_visits, "total_customers": total_customers}


def get_by_id(db: Session, visit_id: uuid.UUID) -> CustomerVisits | None:
    return db.get(CustomerVisits, visit_id)

def create_visit(db: Session, data: CustomerVisitCreate, user_id: uuid.UUID) -> CustomerVisits:
    visit = CustomerVisits(**data.model_dump(), user_id=user_id)
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
