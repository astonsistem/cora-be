from fastapi import Depends

from app.core.response.envelope import ApiRouter
from app.dependencies import get_auth_service
from app.middleware.auth_middleware import get_current_user
from app.models.users import Users
from app.schemas.auth_schema import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user_schema import UserResponse
from app.services.auth_service import AuthService

router = ApiRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(data.username, data.password)

@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return service.refresh(data.refresh_token)

@router.get("/me", response_model=UserResponse)
def me(current_user: Users = Depends(get_current_user)):
    return current_user
