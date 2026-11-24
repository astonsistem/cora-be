import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.integrations.asis_client import AsisClient, AsisGateway
from app.core.security.credential_cipher import CredentialCipher
from app.models.asis_credential import AsisCredentials
from app.models.branches import Branches


class AsisGatewayProvider:
    def __init__(self, db: Session, cipher: CredentialCipher | None = None, client_factory=AsisClient):
        self.db = db
        self.cipher = cipher or CredentialCipher()
        self._client_factory = client_factory
        self._cache: dict[tuple[str, uuid.UUID | None], AsisGateway] = {}

    def default(self) -> AsisGateway:
        return self._cached(("default", None), self._client_factory)

    def for_company(self, company_id: uuid.UUID | None) -> AsisGateway:
        if company_id is None:
            return self.default()
        return self._cached(("company", company_id), lambda: self._build(self._company_credential(company_id)))

    def for_branch(self, branch: Branches | None) -> AsisGateway:
        if branch is None:
            return self.default()
        return self._cached(("branch", branch.branch_id), lambda: self._build(self._branch_credential(branch)))

    def _branch_credential(self, branch: Branches) -> AsisCredentials | None:
        credential = self.db.scalar(select(AsisCredentials).where(AsisCredentials.branch_id == branch.branch_id))
        return credential or self._company_credential(branch.company_id)

    def _company_credential(self, company_id: uuid.UUID | None) -> AsisCredentials | None:
        return self.db.scalar(
            select(AsisCredentials).where(AsisCredentials.company_id == company_id, AsisCredentials.branch_id.is_(None))
        )

    def _build(self, credential: AsisCredentials | None) -> AsisGateway:
        if credential is None:
            return self._client_factory()
        return self._client_factory(credential.username, self.cipher.decrypt(credential.password_encrypted))

    def _cached(self, key, factory) -> AsisGateway:
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]
