import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database.database import Base


class ActivityLogs(Base):
    __tablename__ = "activity_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    user_name = Column(String, nullable=False)
    user_role = Column(String, nullable=False)
    action = Column(String(20), nullable=False)
    module = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    company = relationship("Companies")
    branch = relationship("Branches")

    __table_args__ = (
        Index("ix_activity_logs_created_at", "created_at"),
        Index("ix_activity_logs_company_created", "company_id", "created_at"),
        Index("ix_activity_logs_archived_at", "archived_at"),
    )

    @property
    def company_name(self) -> str | None:
        return self.company.company_name if self.company else None

    @property
    def branch_name(self) -> str | None:
        return self.branch.branch_name if self.branch else None
