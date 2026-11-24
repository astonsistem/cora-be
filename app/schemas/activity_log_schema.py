import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

ROLE_LABELS = {
    "sales": "Sales",
    "branch_manager": "Branch Manager",
    "operasional_manager": "Operational Manager",
    "superadmin": "Super Admin",
}


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: uuid.UUID
    created_at: datetime
    user_name: str
    user_role: str
    action: str
    module: str
    description: str
    company_id: uuid.UUID | None = None
    company_name: str = "-"
    branch_id: uuid.UUID | None = None
    branch_name: str = "-"
    ip_address: str | None = None
    user_agent: str | None = None
    archived_at: datetime | None = None

    @field_validator("user_role")
    @classmethod
    def _role_label(cls, value: str) -> str:
        return ROLE_LABELS.get(value, value)

    @field_validator("company_name", "branch_name", mode="before")
    @classmethod
    def _dash_when_empty(cls, value):
        return value or "-"


class ActivityCompanyOption(BaseModel):
    company_id: uuid.UUID
    name: str


class ActivityBranchOption(BaseModel):
    branch_id: uuid.UUID
    company_id: uuid.UUID
    name: str


class ActivityFilterOptions(BaseModel):
    companies: list[ActivityCompanyOption]
    branches: list[ActivityBranchOption]
