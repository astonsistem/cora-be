import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.integrations.asis_client import AsisClient, AsisGateway
from app.core.security.credential_cipher import CredentialCipher
from app.models.asis_credential import AsisCredentials


class AsisGatewayProvider:
    def __init__(self, db: Session, cipher: CredentialCipher | None = None, client_factory=AsisClient):
        self.db = db
        self.cipher = cipher or CredentialCipher()
        self._client_factory = client_factory
        self._cache: dict[uuid.UUID | None, AsisGateway] = {}

    def default(self) -> AsisGateway:
        return self._cached(None, self._client_factory)

    def for_company(self, company_id: uuid.UUID | None) -> AsisGateway:
        if company_id is None:
            return self.default()
        if company_id not in self._cache:
            self._cache[company_id] = self._build(company_id)
        return self._cache[company_id]

    def _build(self, company_id: uuid.UUID) -> AsisGateway:
        credential = self.db.scalar(select(AsisCredentials).where(AsisCredentials.company_id == company_id))
        if credential is None:
            return self._client_factory()
        return self._client_factory(credential.username, self.cipher.decrypt(credential.password_encrypted))

    def _cached(self, key, factory) -> AsisGateway:
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]
