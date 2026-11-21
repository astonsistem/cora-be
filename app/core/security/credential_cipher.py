from cryptography.fernet import Fernet, InvalidToken

from app.core.config.config import settings
from app.exceptions import BadRequestError


class CredentialCipher:
    def __init__(self, key: str | None = None):
        self._key = key if key is not None else settings.asis_secret_key

    @property
    def _fernet(self) -> Fernet:
        if not self._key:
            raise BadRequestError("ASIS_SECRET_KEY belum diisi di .env")
        try:
            return Fernet(self._key.encode())
        except ValueError:
            raise BadRequestError("ASIS_SECRET_KEY tidak valid, buat ulang dengan Fernet.generate_key()")

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            raise BadRequestError("Password ASIS tidak bisa dibaca, kemungkinan ASIS_SECRET_KEY berubah. Atur ulang akunnya")
