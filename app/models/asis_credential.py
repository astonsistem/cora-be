import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database.database import Base


class AsisCredentials(Base):
    __tablename__ = "asis_credentials"

    credential_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=True)
    username = Column(String(150), nullable=False)
    password_encrypted = Column(String, nullable=False)
    last_verified_at = Column(DateTime, nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Companies")
    branch = relationship("Branches")

    __table_args__ = (
        Index("uq_asis_credentials_company", "company_id", unique=True, postgresql_where=text("branch_id IS NULL")),
        Index("uq_asis_credentials_branch", "branch_id", unique=True),
    )
