import uuid
from sqlalchemy import func, Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database.database import Base

class CustomerVisits(Base):
    __tablename__ = "customer_visits"

    visit_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    posted_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=True, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id"))
    notes = Column(String, nullable=True)
    is_posted_to_asis = Column(Boolean, default=False)
    posted_to_asis_at = Column(DateTime, nullable=True)
    asis_partner_id = Column(String, nullable=True)
    qr_id = Column(UUID(as_uuid=True), ForeignKey("voucher_qrs.qr_id"), nullable=True, index=True)
    meta = Column(JSONB, nullable=False, default=dict, server_default="{}")
    claim_token = Column(String(64), nullable=True, unique=True)
    claim_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("Users")
    customer = relationship("Customers")
    source = relationship("Sources")
    category = relationship("Category")
    qr = relationship("VoucherQrs")
