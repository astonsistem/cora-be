import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.integrations.asis_client import AsisClient, AsisError
from app.core.security.credential_cipher import CredentialCipher
from app.exceptions import BadRequestError, NotFoundError
from app.models.asis_credential import AsisCredentials
from app.models.companies import Companies
from app.models.users import Users
from app.schemas.asis_credential_schema import AsisCredentialSet


class AsisCredentialService:
    def __init__(self, db: Session, cipher: CredentialCipher | None = None, client_factory=AsisClient):
        self.db = db
        self.cipher = cipher or CredentialCipher()
        self._client_factory = client_factory

    def list_all(self, user: Users) -> list[dict]:
        credentials = {c.company_id: c for c in self.db.scalars(select(AsisCredentials))}
        query = select(Companies).where(Companies.deleted_at.is_(None)).order_by(Companies.company_name)
        if not user.is_superadmin:
            query = query.where(Companies.company_id == user.company_id)
        companies = self.db.scalars(query)
        return [self._view(company, credentials.get(company.company_id)) for company in companies]

    def save(self, company_id: uuid.UUID, data: AsisCredentialSet, user: Users) -> dict:
        company = self._company(company_id, user)
        credential = self._credential(company_id)
        password = data.password or self._stored_password(credential)
        self._verify(data.username, password)

        if credential is None:
            credential = AsisCredentials(company_id=company_id, created_by=user.user_id)
            self.db.add(credential)
        credential.username = data.username
        credential.password_encrypted = self.cipher.encrypt(password)
        credential.last_verified_at = datetime.now()
        self.db.commit()
        return self._view(company, credential)

    def remove(self, company_id: uuid.UUID, user: Users) -> None:
        self._company(company_id, user)
        credential = self._credential(company_id)
        if credential is None:
            raise NotFoundError("Akun ASIS untuk company ini belum diatur")
        self.db.delete(credential)
        self.db.commit()

    def _company(self, company_id: uuid.UUID, user: Users) -> Companies:
        company = self.db.get(Companies, company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Company tidak ditemukan")
        if not user.is_superadmin and company.company_id != user.company_id:
            raise NotFoundError("Company tidak ditemukan")
        return company

    def _credential(self, company_id: uuid.UUID) -> AsisCredentials | None:
        return self.db.scalar(select(AsisCredentials).where(AsisCredentials.company_id == company_id))

    def _stored_password(self, credential: AsisCredentials | None) -> str:
        if credential is None:
            raise BadRequestError("Password ASIS wajib diisi")
        return self.cipher.decrypt(credential.password_encrypted)

    def _verify(self, username: str, password: str) -> None:
        try:
            self._client_factory(username, password).login()
        except AsisError as error:
            raise BadRequestError(f"Akun ASIS tidak bisa dipakai login. {error}")

    @staticmethod
    def _view(company: Companies, credential: AsisCredentials | None) -> dict:
        return {
            "company_id": company.company_id,
            "company_name": company.company_name,
            "username": credential.username if credential else None,
            "is_configured": credential is not None,
            "last_verified_at": credential.last_verified_at if credential else None,
        }
