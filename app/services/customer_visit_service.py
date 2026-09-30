import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_visits import CustomerVisits
from app.schemas.customer_visit_schema import CustomerVisitCreate, CustomerVisitUpdate

def get_all(
    db: Session,
    user_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CustomerVisits]:
    query = select(CustomerVisits).order_by(CustomerVisits.posted_at.desc())
    if user_id:
        query = query.where(CustomerVisits.user_id == user_id)
    return list(db.scalars(query.offset(skip).limit(limit)))

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
