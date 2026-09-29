import uuid
from sqlalchemy import func, Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class CustomerVisits(Base):
    __tablename__ = "customer_visits"

    visit_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    posted_at = Column(DateTime, nullable=False, server_default=func.now())
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id"))
    notes = Column(String, nullable=True)
    is_posted_to_asis = Column(Boolean, default=False)
    posted_to_asis_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("Users")
    source = relationship("Sources")
    category = relationship("Category")
