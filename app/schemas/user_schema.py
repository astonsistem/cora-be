import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.users import UserRole

class UserBase(BaseModel):
    first_name: str
    last_name: str
    username: str
    user_role: UserRole
    company_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    photo_url: str | None = None

class UserCreate(UserBase):
    password: str 

class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    password: str | None = None
    user_role: UserRole | None = None
    company_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    photo_url: str | None = None
    is_active: bool | None = None

class UserResponse(UserBase):

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
