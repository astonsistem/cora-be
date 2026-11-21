import enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database.database import Base


class QuestionType(str, enum.Enum):
    rating = "rating"
    text = "text"
    choice = "choice"


class VisitQuestions(Base):
    __tablename__ = "visit_questions"

    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    question = Column(String(300), nullable=False)
    type = Column(String(20), nullable=False)
    answers = Column(JSONB, nullable=False, default=list, server_default="[]")
    is_required = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('rating', 'text', 'choice')", name="ck_visit_questions_type"),
    )
