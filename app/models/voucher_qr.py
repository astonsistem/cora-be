import enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.core.database.database import Base


class VoucherMode(str, enum.Enum):
    single = "single"
    random_one = "random_one"
    all = "all"


class VoucherQrs(Base):
    __tablename__ = "voucher_qrs"

    qr_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id"), nullable=True)
    voucher_mode = Column(String(20), nullable=False, default=VoucherMode.single.value, server_default="single")
    voucher_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}")
    code = Column(String(20), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    is_locked = Column(Boolean, nullable=False, default=False, server_default="false")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies")
    source = relationship("Sources")
    category = relationship("Category")
    branch = relationship("Branches")

    __table_args__ = (
        CheckConstraint("voucher_mode IN ('single', 'random_one', 'all')", name="ck_voucher_qrs_mode"),
    )
