import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class CompanyBase(BaseModel):
    asis_company_id: str
    company_code: str
    company_name: str
    company_address: str

class CompanyCreate(CompanyBase):
    last_synced_at: datetime

class CompanyUpdate(BaseModel):
    asis_company_id: str | None = None
    company_code: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    last_synced_at: datetime | None = None

class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime
