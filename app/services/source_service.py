import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sources import Sources
from app.schemas.source_schema import SourceCreate, SourceUpdate

def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Sources]:
    return list(db.scalars(select(Sources).offset(skip).limit(limit)))

def get_by_id(db: Session, source_id: uuid.UUID) -> Sources | None:
    return db.get(Sources, source_id)

def create_source(db: Session, data: SourceCreate) -> Sources:
    obj = Sources(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_source(db: Session, obj: Sources, data: SourceUpdate) -> Sources:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_source(db: Session, obj: Sources) -> None:
    db.delete(obj)
    db.commit()
