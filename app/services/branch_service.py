import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branches import Branches
from app.schemas.branch_schema import BranchCreate, BranchUpdate

def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Branches]:
    return list(db.scalars(select(Branches).offset(skip).limit(limit)))

def get_by_id(db: Session, branch_id: uuid.UUID) -> Branches | None:
    return db.get(Branches, branch_id)

def create_branch(db: Session, data: BranchCreate) -> Branches:
    obj = Branches(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_branch(db: Session, obj: Branches, data: BranchUpdate) -> Branches:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_branch(db: Session, obj: Branches) -> None:
    db.delete(obj)
    db.commit()
