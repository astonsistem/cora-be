import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class SourceBase(BaseModel):
    name: str
    description: str | None = None

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class SourceResponse(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    source_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
