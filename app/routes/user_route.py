import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.models.users import UserRole, Users
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["User"])

MAX_PHOTO_BYTES = 2 * 1024 * 1024

def _get_or_404(db: Session, user_id: uuid.UUID):
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # OM: semua user, BM: user di branch-nya, sales: dirinya sendiri
    return user_service.get_all(db, current_user, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    return _get_or_404(db, user_id)


def _require_self_or_om(current_user: Users, user_id: uuid.UUID):
    if current_user.user_role != UserRole.operasional_manager and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")


def _sniff_image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/{user_id}/photo")
def get_user_photo(user_id: uuid.UUID, db: Session = Depends(get_db)):
    # Tanpa auth supaya bisa dipakai langsung di <img src>; user_id berupa UUID.
    photo = user_service.get_photo(db, user_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(
        content=photo.data,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=0, must-revalidate"},
    )


@router.put("/{user_id}/photo", response_model=UserResponse)
async def upload_user_photo(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    user = _get_or_404(db, user_id)

    data = await file.read(MAX_PHOTO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail=f"Photo must be at most {MAX_PHOTO_BYTES // (1024 * 1024)} MB")

    content_type = _sniff_image_type(data)
    if not content_type:
        raise HTTPException(status_code=415, detail="Photo must be a JPEG, PNG, or WebP image")

    return user_service.save_photo(db, user, content_type, data)


@router.delete("/{user_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_photo(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    user = _get_or_404(db, user_id)
    user_service.delete_photo(db, user)


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
