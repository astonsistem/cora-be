import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

class CustomerVisitBase(BaseModel):
    customer_name: str
    phone: str
    source_id: uuid.UUID
    category_id: uuid.UUID
    notes: str | None = None

class CustomerVisitCreate(BaseModel):
    # Pilih customer dari Master Customer (customer_id), atau isi nama dan telepon untuk customer baru
    # (otomatis masuk Master Customer). branch_id hanya dipakai untuk customer baru: wajib bagi OM,
    # Sales dan BM otomatis memakai branch profilnya.
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    phone: str | None = None
    branch_id: uuid.UUID | None = None
    source_id: uuid.UUID
    category_id: uuid.UUID
    notes: str | None = None

    @model_validator(mode="after")
    def _customer_required(self):
        if self.customer_id is None and not (self.customer_name and self.phone):
            raise ValueError("Pilih customer atau isi customer_name dan phone")
        return self

class CustomerVisitUpdate(BaseModel):
    customer_name: str | None = None
    phone: str | None = None
    source_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    notes: str | None = None

class CustomerVisitResponse(CustomerVisitBase):
    model_config = ConfigDict(from_attributes=True)

    visit_id: uuid.UUID
    user_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    posted_at: datetime
    is_posted_to_asis: bool
    posted_to_asis_at: datetime | None = None
    asis_partner_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CustomerVisitSummary(BaseModel):
    total_visits: int
    total_customers: int
