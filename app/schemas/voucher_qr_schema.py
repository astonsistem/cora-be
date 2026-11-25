import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.visit_question import QuestionType
from app.models.voucher_qr import VoucherMode


class VoucherQrBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    branch_id: uuid.UUID | None = None
    source_id: uuid.UUID
    category_id: uuid.UUID | None = None
    voucher_mode: VoucherMode = VoucherMode.single
    voucher_ids: list[uuid.UUID] = Field(min_length=1)
    is_active: bool = True


class VoucherQrCreate(VoucherQrBase):
    company_id: uuid.UUID | None = None


class VoucherQrUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    branch_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    voucher_mode: VoucherMode | None = None
    voucher_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    is_locked: bool | None = None


class VoucherQrResponse(VoucherQrBase):
    model_config = ConfigDict(from_attributes=True)

    qr_id: uuid.UUID
    company_id: uuid.UUID
    code: str
    is_locked: bool = False
    created_at: datetime
    updated_at: datetime


class VisitQuestionItem(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    type: QuestionType
    answers: list[str] = Field(default_factory=list)
    is_required: bool = False


class VisitQuestionsReplace(BaseModel):
    company_id: uuid.UUID | None = None
    questions: list[VisitQuestionItem]


class VisitQuestionResponse(VisitQuestionItem):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID
    sort_order: int


class QrCategoryOption(BaseModel):
    category_id: uuid.UUID
    name: str


class QrVoucherPreview(BaseModel):
    voucher_id: uuid.UUID
    voucher_name: str
    description: str | None = None
    date_expired: date
    design: dict | None = None
    state: str
    claimable: bool


class QrPublicInfo(BaseModel):
    name: str
    company_name: str
    category_id: uuid.UUID | None = None
    categories: list[QrCategoryOption]
    questions: list[VisitQuestionResponse]
    voucher_mode: VoucherMode
    vouchers: list[QrVoucherPreview]


class QrAnswer(BaseModel):
    question_id: uuid.UUID
    answer: str = ""


class QrSubmit(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=30)
    address: str = Field(min_length=1, max_length=300)
    category_id: uuid.UUID | None = None
    answers: list[QrAnswer] = Field(default_factory=list)


class QrSubmitResult(BaseModel):
    claim_token: str
    expires_at: datetime


class QrClaimRequest(BaseModel):
    voucher_id: uuid.UUID | None = None


class IssuedVoucher(BaseModel):
    voucher_id: uuid.UUID
    voucher_name: str
    description: str | None = None
    date_expired: date
    design: dict | None = None
    code: str


class IssuedVouchers(BaseModel):
    vouchers: list[IssuedVoucher]


class QrLinkTarget(BaseModel):
    qr_code: str
