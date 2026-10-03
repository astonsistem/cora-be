import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class CustomerVisitBase(BaseModel):
    customer_name: str
    phone: str
    source_id: uuid.UUID
    category_id: uuid.UUID
    notes: str | None = None

class CustomerVisitCreate(CustomerVisitBase):
    pass 

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
    posted_at: datetime
    is_posted_to_asis: bool
    posted_to_asis_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CustomerVisitSummary(BaseModel):
    total_visits: int
    total_customers: int
