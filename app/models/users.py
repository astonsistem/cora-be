import uuid
import enum
from sqlalchemy import func, Column, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    sales = "sales"
    branch_manager = "branch_manager"
    operasional_manager = "operasional_manager"

class Users(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    user_role = Column(Enum(UserRole, name="user_role"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"))
    photo_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies")
    branch = relationship("Branches", back_populates="users")