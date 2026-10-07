import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import settings
from app.exceptions import UnauthorizedError

api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

class ApiKeyChecker:
    def __init__(self, valid_keys: tuple[str, ...] | None = None):
        self._valid_keys = valid_keys

    @property
    def valid_keys(self) -> tuple[str, ...]:
        return settings.public_api_keys if self._valid_keys is None else self._valid_keys

    def _matches(self, api_key: str) -> bool:
        candidate = api_key.encode()
        return any([secrets.compare_digest(candidate, key.encode()) for key in self.valid_keys])

    def __call__(self, api_key: str | None = Security(api_key_header)) -> str:
        if not api_key or not self._matches(api_key):
            raise UnauthorizedError("Invalid or missing API key")
        return api_key

api_key_required = ApiKeyChecker()
