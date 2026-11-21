import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.voucher import ClaimFlag, ClaimStatus, VoucherStatus


class VoucherBase(BaseModel):
    voucher_name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    quota_voucher: int = Field(ge=0)
    status: VoucherStatus = VoucherStatus.active
    date_started: date
    date_expired: date
    branch_ids: list[uuid.UUID] | None = None
    design: dict | None = None

    @model_validator(mode="after")
    def _check_range(self):
        if self.date_expired < self.date_started:
            raise ValueError("date_expired tidak boleh lebih awal dari date_started")
        return self


class VoucherCreate(VoucherBase):
    company_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=3, max_length=40)


class VoucherDesignUpdate(BaseModel):
    design: dict | None = None


class VoucherUpdate(BaseModel):
    voucher_name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    quota_voucher: int | None = Field(default=None, ge=0)
    status: VoucherStatus | None = None
    date_started: date | None = None
    date_expired: date | None = None
    branch_ids: list[uuid.UUID] | None = None
    qr_target_id: uuid.UUID | None = None
    design: dict | None = None


class VoucherResponse(VoucherBase):
    model_config = ConfigDict(from_attributes=True)

    voucher_id: uuid.UUID
    company_id: uuid.UUID
    code: str
    used_count: int
    qr_slug: str | None = None
    qr_target_id: uuid.UUID | None = None
    sold_out_at: datetime | None = None
    archived_at: datetime | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def remaining(self) -> int:
        return max(self.quota_voucher - self.used_count, 0)


class ClaimRecord(BaseModel):
    claim_id: uuid.UUID
    code: str
    customer_name: str
    customer_phone: str
    voucher_name: str
    branch_name: str
    claimed_at: datetime
    redeemed_at: datetime | None = None
    cancelled_at: datetime | None = None
    redeemed_by: uuid.UUID | None = None
    redeemed_by_name: str | None = None
    status: ClaimStatus
    flag_reason: ClaimFlag | None = None


class ClaimCreate(BaseModel):
    code: str = Field(min_length=1)
    branch_id: uuid.UUID | None = None
    redeem: bool = False


class PublicClaimCreate(BaseModel):
    branch_id: uuid.UUID


class ClaimHistoryItem(BaseModel):
    claim_id: uuid.UUID
    branch_id: uuid.UUID
    branch_name: str
    status: ClaimStatus
    claimed_at: datetime
    redeemed_at: datetime | None = None
    cancelled_at: datetime | None = None


class BranchOption(BaseModel):
    branch_id: uuid.UUID
    branch_name: str


class CodeView(BaseModel):
    code: str
    voucher_name: str
    date_expired: date
    expired: bool
    customer_name: str
    branches: list[BranchOption]
    claims: list[ClaimHistoryItem]
    active_claim: ClaimHistoryItem | None = None
