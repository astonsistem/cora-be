import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users import Users
from app.schemas.user_schema import UserCreate, UserUpdate
from app.security import hash_password

def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Users]:
    return list(db.scalars(select(Users).offset(skip).limit(limit)))

def get_by_id(db: Session, user_id: uuid.UUID) -> Users | None:
    return db.get(Users, user_id)

def get_by_username(db: Session, username: str) -> Users | None:
    return db.scalar(select(Users).where(Users.username == username))

def create_user(db: Session, data: UserCreate) -> Users:
    if get_by_username(db, data.username):
        raise ValueError("Username already exists")

    values = data.model_dump(exclude={"password"})
    user = Users(**values, password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user: Users, data: UserUpdate) -> Users:
    values = data.model_dump(exclude_unset=True)

    new_username = values.get("username")
    if new_username and new_username != user.username and get_by_username(db, new_username):
        raise ValueError("Username already exists")

    if "password" in values:
        values["password"] = hash_password(values["password"])

    for key, value in values.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: Users) -> None:
    db.delete(user)
    db.commit()
