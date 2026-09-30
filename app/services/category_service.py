import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category_schema import CategoryCreate, CategoryUpdate

def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Category]:
    return list(db.scalars(select(Category).offset(skip).limit(limit)))

def get_by_id(db: Session, category_id: uuid.UUID) -> Category | None:
    return db.get(Category, category_id)

def create_category(db: Session, data: CategoryCreate) -> Category:
    obj = Category(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_category(db: Session, obj: Category, data: CategoryUpdate) -> Category:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

def delete_category(db: Session, obj: Category) -> None:
    db.delete(obj)
    db.commit()
