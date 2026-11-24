import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class AsisCredentialSet(BaseModel):
    username: str
    password: str | None = None

    @field_validator("username")
    @classmethod
    def _username_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username ASIS wajib diisi")
        return value

    @field_validator("password")
    @classmethod
    def _password_empty_as_none(cls, value: str | None) -> str | None:
        return value or None


class AsisBranchCredentialResponse(BaseModel):
    branch_id: uuid.UUID
    branch_name: str
    company_id: uuid.UUID
    company_name: str
    username: str | None = None
    is_configured: bool
    last_verified_at: datetime | None = None


class AsisCredentialResponse(BaseModel):
    company_id: uuid.UUID
    company_name: str
    username: str | None = None
    is_configured: bool
    last_verified_at: datetime | None = None
