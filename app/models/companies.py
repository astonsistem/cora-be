import uuid
from sqlalchemy import func, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Companies(Base):
    __tablename__ = "companies"

    company_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    asis_company_id = Column(String, nullable=False)
    company_code = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    company_address = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_synced_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    branches = relationship("Branches", back_populates="company")