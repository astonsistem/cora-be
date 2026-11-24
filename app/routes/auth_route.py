from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.response.envelope import ApiRouter
from app.core.database.database import get_db
from app.dependencies import get_activity_logger, get_auth_service
from app.middleware.auth_middleware import get_current_user
from app.models.users import Users
from app.schemas.auth_schema import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user_schema import ProfileResponse
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.auth_service import AuthService

router = ApiRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    tokens = service.login(data.username, data.password)
    user = service.users.get_by_username(data.username)
    ActivityLogger(db, user, request).record(Action.login, Module.auth, "Login ke CORA")
    return tokens

@router.post("/logout")
def logout(activity: ActivityLogger = Depends(get_activity_logger)):
    activity.record(Action.logout, Module.auth, "Logout dari CORA")

@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return service.refresh(data.refresh_token)

@router.get("/me", response_model=ProfileResponse)
def me(current_user: Users = Depends(get_current_user)):
    return current_user
