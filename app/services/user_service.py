import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_photos import UserPhotos
from app.models.users import UserRole, Users
from app.schemas.user_schema import UserCreate, UserUpdate
from app.security import hash_password

def get_all(db: Session, current_user: Users, skip: int = 0, limit: int = 100) -> list[Users]:
    query = select(Users)
    if current_user.user_role == UserRole.sales or (
        current_user.user_role == UserRole.branch_manager and current_user.branch_id is None
    ):
        query = query.where(Users.user_id == current_user.user_id)
    elif current_user.user_role == UserRole.branch_manager:
        query = query.where(Users.branch_id == current_user.branch_id)
    return list(db.scalars(query.offset(skip).limit(limit)))

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

def get_photo(db: Session, user_id: uuid.UUID) -> UserPhotos | None:
    return db.get(UserPhotos, user_id)

def save_photo(db: Session, user: Users, content_type: str, data: bytes) -> Users:
    photo = db.get(UserPhotos, user.user_id)
    if photo:
        photo.content_type = content_type
        photo.data = data
    else:
        db.add(UserPhotos(user_id=user.user_id, content_type=content_type, data=data))
    user.photo_url = f"/users/{user.user_id}/photo"
    db.commit()
    db.refresh(user)
    return user

def delete_photo(db: Session, user: Users) -> None:
    photo = db.get(UserPhotos, user.user_id)
    if photo:
        db.delete(photo)
    user.photo_url = None
    db.commit()

def delete_user(db: Session, user: Users) -> None:
    db.delete(user)
    db.commit()
