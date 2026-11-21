import uuid
from sqlalchemy import func, Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database.database import Base
from app.core.soft_delete import SoftDeleteMixin

class Category(SoftDeleteMixin, Base):
    __tablename__ = "category"

    category_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=True, index=True)
    asis_category_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies")

    __table_args__ = (UniqueConstraint("company_id", "asis_category_id", name="uq_category_company_asis"),)
