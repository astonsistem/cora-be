import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

class TokenService:
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, expire_minutes: int):
        self.secret_key = secret_key
        self.expire_minutes = expire_minutes

    def create_access_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)

    def decode_access_token(self, token: str) -> uuid.UUID:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
        return uuid.UUID(payload["sub"])

password_hasher = PasswordHasher()
token_service = TokenService(settings.secret_key, settings.access_token_expire_minutes)
