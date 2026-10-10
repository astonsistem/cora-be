import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.dependencies import get_user_service
from app.exceptions import BadRequestError, ForbiddenError, NotFoundError, PayloadTooLargeError, UnsupportedMediaError
from app.middleware.auth_middleware import admin_only, get_current_user
from app.models.users import UserRole, Users
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User"])

MAX_PHOTO_BYTES = 2 * 1024 * 1024

def _require_self_or_om(current_user: Users, user_id: uuid.UUID):
    if current_user.user_role != UserRole.operasional_manager and current_user.user_id != user_id:
        raise ForbiddenError("You do not have permission to perform this action")

def _sniff_image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None

@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: UserRole | None = None,
    service: UserService = Depends(get_user_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_all_for(current_user, skip=skip, limit=limit, role=role)

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    return service.get_or_404(user_id)

@router.get("/{user_id}/photo")
def get_user_photo(user_id: uuid.UUID, service: UserService = Depends(get_user_service)):
    photo = service.get_photo(user_id)
    if not photo:
        return Response(status_code=204)
    return Response(
        content=photo.data,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=0, must-revalidate"},
    )

@router.put("/{user_id}/photo", response_model=UserResponse)
async def upload_user_photo(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    service: UserService = Depends(get_user_service),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    user = service.get_or_404(user_id)

    data = await file.read(MAX_PHOTO_BYTES + 1)
    if not data:
        raise BadRequestError("Empty file")
    if len(data) > MAX_PHOTO_BYTES:
        raise PayloadTooLargeError(f"Photo must be at most {MAX_PHOTO_BYTES // (1024 * 1024)} MB")

    content_type = _sniff_image_type(data)
    if not content_type:
        raise UnsupportedMediaError("Photo must be a JPEG, PNG, or WebP image")

    return service.save_photo(user, content_type, data)

@router.delete("/{user_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_photo(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    current_user: Users = Depends(get_current_user),
):
    _require_self_or_om(current_user, user_id)
    service.delete_photo(service.get_or_404(user_id))

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_user(data: UserCreate, service: UserService = Depends(get_user_service)):
    return service.create(data)

@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_only)])
def update_user(user_id: uuid.UUID, data: UserUpdate, service: UserService = Depends(get_user_service)):
    return service.update(service.get_or_404(user_id), data)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_user(user_id: uuid.UUID, service: UserService = Depends(get_user_service)):
    service.delete(service.get_or_404(user_id))
