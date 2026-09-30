import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class BranchBase(BaseModel):
    asis_branch_id: str
    company_id: uuid.UUID
    branch_code: str
    branch_name: str
    branch_address: str

class BranchCreate(BranchBase):
    last_synced_at: datetime

class BranchUpdate(BaseModel):
    asis_branch_id: str | None = None
    company_id: uuid.UUID | None = None
    branch_code: str | None = None
    branch_name: str | None = None
    branch_address: str | None = None
    last_synced_at: datetime | None = None

class BranchResponse(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    branch_id: uuid.UUID
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime
