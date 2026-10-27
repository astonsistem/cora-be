import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class VoucherBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    quota: int = Field(ge=0)
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _check_range(self):
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until tidak boleh lebih awal dari valid_from")
        return self


class VoucherCreate(VoucherBase):
    # Wajib bagi OM; Branch Manager otomatis memakai branch profilnya
    branch_id: uuid.UUID | None = None


class VoucherUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    quota: int | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool | None = None


class VoucherResponse(VoucherBase):
    model_config = ConfigDict(from_attributes=True)

    voucher_id: uuid.UUID
    branch_id: uuid.UUID
    used_count: int
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def remaining(self) -> int:
        return max(self.quota - self.used_count, 0)


class RedemptionStatus(str, Enum):
    pending = "pending"
    redeemed = "redeemed"
    cancelled = "cancelled"


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    redemption_id: uuid.UUID
    voucher_id: uuid.UUID
    full_name: str
    phone: str
    phone_norm: str
    status: str
    submitted_at: datetime


class RedemptionStatusUpdate(BaseModel):
    status: RedemptionStatus


# ---- Untuk Google Form (endpoint publik) ----

class PublicVoucherItem(BaseModel):
    voucher_id: uuid.UUID
    label: str
    remaining: int


class PublicRedemptionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=30)
    voucher_label: str = Field(min_length=1)


class PublicRedemptionResult(BaseModel):
    status: str = "ok"
    message: str