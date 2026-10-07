from fastapi import APIRouter, Depends

from app.dependencies import get_user_service
from app.exceptions import UnauthorizedError
from app.middleware.auth_middleware import get_current_user
from app.models.users import Users
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.user_schema import UserResponse
from app.security import password_hasher, token_service
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: UserService = Depends(get_user_service)):
    user = service.get_by_username(data.username)
    if not user or not user.is_active or not password_hasher.verify(data.password, user.password):
        raise UnauthorizedError("Invalid username or password")
    return TokenResponse(access_token=token_service.create_access_token(user.user_id))

@router.get("/me", response_model=UserResponse)
def me(current_user: Users = Depends(get_current_user)):
    return current_user
