import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["User"])

def _get_or_404(db: Session, user_id: uuid.UUID):
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=list[UserResponse], dependencies=[Depends(admin_only)])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.get_all(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_only)])
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, user_id)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    try:
        return user_service.create_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid company or branch reference")


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_only)])
def update_user(user_id: uuid.UUID, data: UserUpdate, db: Session = Depends(get_db)):
    user = _get_or_404(db, user_id)
    try:
        return user_service.update_user(db, user, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid company or branch reference")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = _get_or_404(db, user_id)
    try:
        user_service.delete_user(db, user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User is still referenced by other data")
