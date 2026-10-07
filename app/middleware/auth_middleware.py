import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ForbiddenError
from app.models.users import UserRole, Users
from app.security import token_service
from app.services.user_service import UserService

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Users:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = token_service.decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized

    user = UserService(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


class RoleChecker:
    def __init__(self, *roles: UserRole):
        self.roles = roles

    def __call__(self, current_user: Users = Depends(get_current_user)) -> Users:
        if current_user.user_role not in self.roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return current_user

admin_only = RoleChecker(UserRole.operasional_manager)
manager_only = RoleChecker(UserRole.operasional_manager, UserRole.branch_manager)
