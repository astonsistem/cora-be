import jwt

from app.exceptions import UnauthorizedError
from app.models.users import Users
from app.schemas.auth_schema import TokenResponse
from app.core.security.security import PasswordHasher, TokenService, password_hasher, token_service
from app.services.user_service import UserService

class AuthService:
    def __init__(
        self,
        users: UserService,
        tokens: TokenService = token_service,
        hasher: PasswordHasher = password_hasher,
    ):
        self.users = users
        self.tokens = tokens
        self.hasher = hasher

    def login(self, username: str, password: str) -> TokenResponse:
        user = self.users.get_by_username(username)
        if not user or not user.is_active or not self.hasher.verify(password, user.password):
            raise UnauthorizedError("Invalid username or password")
        return self._issue(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            user_id = self.tokens.decode_refresh_token(refresh_token)
        except (jwt.PyJWTError, ValueError, KeyError):
            raise UnauthorizedError("Invalid or expired refresh token")
        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("Invalid or expired refresh token")
        return self._issue(user)

    def _issue(self, user: Users) -> TokenResponse:
        return TokenResponse(
            access_token=self.tokens.create_access_token(user.user_id),
            refresh_token=self.tokens.create_refresh_token(user.user_id),
        )
