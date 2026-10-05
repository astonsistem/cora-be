from pydantic import BaseModel, Field


class AsisApplyRequest(BaseModel):
    company_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    # None (tidak dikirim) = terapkan semua kategori dari ASIS, [] = tidak ada kategori.
    category_ids: list[str] | None = None
