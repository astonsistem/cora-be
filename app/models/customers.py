import re
import unicodedata
import uuid

from sqlalchemy import func, Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.database import Base

def normalize_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", text).strip().casefold()

def normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return "0" + digits[2:] if digits.startswith("62") else digits

def phones_match(a: str | None, b: str | None) -> bool:
    return not a or not b or a == b

class Customers(Base):
    __tablename__ = "customers"

    customer_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    asis_partner_id = Column(String, nullable=True, unique=True)
    name = Column(String, nullable=False)
    name_search = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    phone_norm = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    branch = relationship("Branches")
    category = relationship("Category")

    @validates("name")
    def _set_name(self, key, value):
        self.name_search = normalize_name(value)
        return value

    @validates("phone")
    def _set_phone(self, key, value):
        self.phone_norm = normalize_phone(value) or None
        return value

    @property
    def status(self) -> str:
        return "posted" if self.asis_partner_id else "pending"
