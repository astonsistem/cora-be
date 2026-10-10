import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class CustomerBase(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    category_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def _name_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nama customer wajib diisi")
        return value

    @field_validator("phone", "email")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        return _clean(value)


class CustomerCreate(CustomerBase):
    # Sales dan BM otomatis memakai branch profilnya, OM wajib memilih branch.
    branch_id: uuid.UUID | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    category_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Nama customer tidak boleh kosong")
        return value.strip() if value else value

    @field_validator("phone", "email")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        return _clean(value)


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    customer_id: uuid.UUID
    branch_id: uuid.UUID
    asis_partner_id: str | None = None
    status: str
    created_by: uuid.UUID | None = None
    posted_at: datetime | None = None
    deleted_at: datetime | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CustomerPostResponse(CustomerResponse):
    # True kalau customer ternyata sudah ada di ASIS sehingga hanya ditautkan, tanpa POST baru.
    linked_existing: bool = False


class CustomerSyncRequest(BaseModel):
    branch_id: uuid.UUID | None = None
