import uuid
from sqlalchemy import func, Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Branches(Base):
    __tablename__ = "branches"

    branch_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    asis_branch_id = Column(String, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"))
    branch_code = Column(String, nullable=False)
    branch_name = Column(String, nullable=False)
    branch_address = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_synced_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies", back_populates="branches")
    users = relationship("Users", back_populates="branch")
