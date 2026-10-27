import uuid
from sqlalchemy import (
    func, Column, String, Text, Integer, Date, DateTime, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Vouchers(Base):
    __tablename__ = "vouchers"

    voucher_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    quota = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False, default=0, server_default="0")
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    redemptions = relationship("VoucherRedemptions", back_populates="voucher")

    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_vouchers_branch_name"),
        CheckConstraint("quota >= 0", name="ck_vouchers_quota"),
        CheckConstraint("used_count >= 0 AND used_count <= quota", name="ck_vouchers_used_count"),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_vouchers_valid_range",
        ),
        Index("ix_vouchers_branch_active", "branch_id", "is_active"),
    )


class VoucherRedemptions(Base):
    __tablename__ = "voucher_redemptions"

    redemption_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    voucher_id = Column(UUID(as_uuid=True), ForeignKey("vouchers.voucher_id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    phone_norm = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    submitted_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    voucher = relationship("Vouchers", back_populates="redemptions")

    __table_args__ = (
        UniqueConstraint("phone_norm", name="uq_voucher_redemptions_phone_norm"),
        CheckConstraint(
            "status IN ('pending', 'redeemed', 'cancelled')",
            name="ck_voucher_redemptions_status",
        ),
        Index("ix_voucher_redemptions_voucher", "voucher_id"),
    )