from pydantic import BaseModel, Field


class AsisApplyRequest(BaseModel):
    company_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] | None = None
