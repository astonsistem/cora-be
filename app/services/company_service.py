import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.companies import Companies
from app.schemas.company_schema import CompanyCreate, CompanyUpdate

def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Companies]:
    return list(db.scalars(select(Companies).offset(skip).limit(limit)))

def get_by_id(db: Session, company_id: uuid.UUID) -> Companies | None:
    return db.get(Companies, company_id)

def create_company(db: Session, data: CompanyCreate) -> Companies:
    obj = Companies(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_company(db: Session, obj: Companies, data: CompanyUpdate) -> Companies:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_company(db: Session, obj: Companies) -> None:
    db.delete(obj)
    db.commit()
