import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config.config import settings

class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt(),
        ).decode()

    def verify(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(
            password.encode(),
            hashed.encode(),
        )

class TokenService:
    ALGORITHM = "HS256"

    def __init__(
        self,
        secret_key: str,
        expire_minutes: int = 15,
        refresh_expire_days: int = 1,
    ):
        self.secret_key = secret_key
        self.expire_minutes = expire_minutes
        self.refresh_expire_days = refresh_expire_days

    def _create_token(
        self,
        user_id: uuid.UUID,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.ALGORITHM,
        )

    def create_access_token(self, user_id: uuid.UUID) -> str:
        return self._create_token(
            user_id=user_id,
            token_type="access",
            expires_delta=timedelta(
                minutes=self.expire_minutes
            ),
        )

    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        return self._create_token(
            user_id=user_id,
            token_type="refresh",
            expires_delta=timedelta(
                days=self.refresh_expire_days
            ),
        )

    def _decode_token(
        self,
        token: str,
        expected_type: str,
    ) -> uuid.UUID:
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.ALGORITHM],
        )

        if payload.get("type") != expected_type:
            raise jwt.InvalidTokenError("Invalid token type")

        return uuid.UUID(payload["sub"])

    def decode_access_token(self, token: str) -> uuid.UUID:
        return self._decode_token(token, "access")

    def decode_refresh_token(self, token: str) -> uuid.UUID:
        return self._decode_token(token, "refresh")


password_hasher = PasswordHasher()

token_service = TokenService(
    secret_key=settings.secret_key,
    expire_minutes=settings.access_token_expire_minutes,
    refresh_expire_days=settings.refresh_token_expire_days,
)
