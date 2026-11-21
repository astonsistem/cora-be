import enum
import uuid

from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database.database import Base


class VoucherStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ClaimStatus(str, enum.Enum):
    claimed = "CLAIMED"
    redeemed = "REDEEMED"
    cancelled = "CANCELLED"


class ClaimFlag(str, enum.Enum):
    phone_name_mismatch = "PHONE_NAME_MISMATCH"
    multiple_match = "MULTIPLE_MATCH"


class ClaimChannel(str, enum.Enum):
    customer = "customer"
    staff = "staff"


def _values(enum_class: type[enum.Enum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_class)


class Vouchers(Base):
    __tablename__ = "vouchers"

    voucher_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    code = Column(String(40), nullable=False, unique=True)
    voucher_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    quota_voucher = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(20), nullable=False, default=VoucherStatus.active.value, server_default="active")
    date_started = Column(Date, nullable=False)
    date_expired = Column(Date, nullable=False)
    branch_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    qr_slug = Column(String(40), nullable=True, unique=True)
    qr_target_id = Column(UUID(as_uuid=True), ForeignKey("voucher_qrs.qr_id"), nullable=True)
    design = Column(JSONB, nullable=True)
    sold_out_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies")
    codes = relationship("VoucherCodes", back_populates="voucher")

    __table_args__ = (
        UniqueConstraint("company_id", "voucher_name", name="uq_vouchers_company_name"),
        CheckConstraint("quota_voucher >= 0", name="ck_vouchers_quota"),
        CheckConstraint("used_count >= 0 AND used_count <= quota_voucher", name="ck_vouchers_used_count"),
        CheckConstraint("date_expired >= date_started", name="ck_vouchers_date_range"),
        CheckConstraint(f"status IN ({_values(VoucherStatus)})", name="ck_vouchers_status"),
        Index("ix_vouchers_company_status", "company_id", "status"),
    )

    @property
    def remaining(self) -> int:
        return max(self.quota_voucher - self.used_count, 0)


class VoucherCodes(Base):
    __tablename__ = "voucher_codes"

    code_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)
    voucher_id = Column(UUID(as_uuid=True), ForeignKey("vouchers.voucher_id"), nullable=False, index=True)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("customer_visits.visit_id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=True, index=True)
    issued_at = Column(DateTime, nullable=False, server_default=func.now())

    voucher = relationship("Vouchers", back_populates="codes")
    visit = relationship("CustomerVisits")
    claims = relationship("VoucherClaims", back_populates="code_ref", order_by="VoucherClaims.claimed_at.desc()")

    @property
    def active_claim(self) -> "VoucherClaims | None":
        for claim in self.claims:
            if claim.status != ClaimStatus.cancelled.value:
                return claim
        return None


class VoucherClaims(Base):
    __tablename__ = "voucher_claims"

    claim_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_id = Column(UUID(as_uuid=True), ForeignKey("voucher_codes.code_id"), nullable=False, index=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=ClaimStatus.claimed.value, server_default="CLAIMED")
    claimed_via = Column(String(20), nullable=False, default=ClaimChannel.customer.value)
    flag_reason = Column(String(40), nullable=True)
    claimed_at = Column(DateTime, nullable=False, server_default=func.now())
    redeemed_at = Column(DateTime, nullable=True)
    redeemed_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    code_ref = relationship("VoucherCodes", back_populates="claims")
    branch = relationship("Branches")
    redeemer = relationship("Users", foreign_keys=[redeemed_by])

    __table_args__ = (
        CheckConstraint(f"status IN ({_values(ClaimStatus)})", name="ck_voucher_claims_status"),
        CheckConstraint(f"claimed_via IN ({_values(ClaimChannel)})", name="ck_voucher_claims_via"),
        Index(
            "uq_voucher_claims_active_code",
            "code_id",
            unique=True,
            postgresql_where=text("status <> 'CANCELLED'"),
        ),
    )

    @property
    def is_flagged(self) -> bool:
        return self.flag_reason is not None
