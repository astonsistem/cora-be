import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.category import Category
from app.models.customer_visits import CustomerVisits
from app.models.visit_question import VisitQuestions
from app.models.voucher import Vouchers
from app.models.voucher_qr import VoucherQrs
from app.schemas.voucher_qr_schema import QrSubmit
from app.services.answer_sheet import AnswerSheet
from app.services.category_guard import CategoryGuard
from app.services.claim_customer import VisitCustomerRegistrar
from app.services.voucher_availability import VoucherAvailability
from app.utils.phone import InvalidPhoneError, normalize_phone


class QrVisitService:
    CLAIM_WINDOW = timedelta(hours=24)

    def __init__(self, db: Session, availability: VoucherAvailability | None = None):
        self.db = db
        self.availability = availability or VoucherAvailability()

    def _active_qr(self, code: str) -> VoucherQrs:
        qr = self.db.scalar(select(VoucherQrs).where(VoucherQrs.code == code))
        if qr is None:
            raise NotFoundError("QR ini sudah tidak berlaku. Silakan minta QR terbaru kepada petugas.")
        if not qr.is_active:
            raise ConflictError("QR ini sedang dinonaktifkan. Silakan hubungi petugas.")
        return qr

    def _questions(self, qr: VoucherQrs) -> list[VisitQuestions]:
        query = (
            select(VisitQuestions)
            .where(VisitQuestions.company_id == qr.company_id)
            .order_by(VisitQuestions.sort_order, VisitQuestions.created_at)
        )
        return list(self.db.scalars(query))

    def _resolve_category(self, qr: VoucherQrs, category_id):
        resolved = qr.category_id or category_id
        if resolved is None:
            raise BadRequestError("Category wajib dipilih")
        CategoryGuard(self.db).ensure_in_company(resolved, qr.company_id)
        return resolved

    def info(self, code: str) -> dict:
        qr = self._active_qr(code)
        categories = list(
            self.db.scalars(
                select(Category)
                .where(Category.company_id == qr.company_id, Category.deleted_at.is_(None))
                .order_by(Category.name)
            )
        )
        return {
            "name": qr.name,
            "company_name": qr.company.company_name,
            "category_id": qr.category_id,
            "categories": [
                {"category_id": item.category_id, "name": item.name} for item in categories
            ],
            "questions": self._questions(qr),
            "voucher_mode": qr.voucher_mode,
            "vouchers": self._voucher_previews(qr),
        }

    def _voucher_previews(self, qr: VoucherQrs) -> list[dict]:
        vouchers = self.db.scalars(
            select(Vouchers)
            .where(Vouchers.voucher_id.in_(qr.voucher_ids), Vouchers.company_id == qr.company_id)
            .order_by(Vouchers.voucher_name)
        )
        return [self._preview(voucher) for voucher in vouchers]

    def _preview(self, voucher: Vouchers) -> dict:
        state = self.availability.state(voucher)
        return {
            "voucher_id": voucher.voucher_id,
            "voucher_name": voucher.voucher_name,
            "description": voucher.description,
            "date_expired": voucher.date_expired,
            "design": voucher.design,
            "state": state,
            "claimable": state == "active",
        }

    def submit(self, code: str, data: QrSubmit) -> dict:
        qr = self._active_qr(code)
        try:
            phone = normalize_phone(data.phone)
        except InvalidPhoneError:
            raise BadRequestError("Nomor telepon tidak valid")

        answers = AnswerSheet(self._questions(qr), data.answers).build()
        visit = CustomerVisits(
            user_id=None,
            customer_name=data.name,
            phone=phone,
            source_id=qr.source_id,
            category_id=self._resolve_category(qr, data.category_id),
            qr_id=qr.qr_id,
            meta={"answers": answers, "voucher_codes": []},
            claim_token=secrets.token_urlsafe(24),
            claim_expires_at=datetime.now() + self.CLAIM_WINDOW,
        )
        self.db.add(visit)
        self.db.flush()
        VisitCustomerRegistrar(self.db).register(visit, qr)
        self.db.commit()
        return {"claim_token": visit.claim_token, "expires_at": visit.claim_expires_at}

    def resolve_link(self, slug: str) -> dict:
        voucher = self.db.scalar(select(Vouchers).where(Vouchers.qr_slug == slug))
        if voucher is None or voucher.qr_target_id is None:
            raise NotFoundError("Link QR tidak ditemukan")
        return {"qr_code": self._active_qr_by_id(voucher.qr_target_id).code}

    def _active_qr_by_id(self, qr_id) -> VoucherQrs:
        qr = self.db.get(VoucherQrs, qr_id)
        if qr is None or not qr.is_active:
            raise ConflictError("QR tujuan sedang tidak aktif")
        return qr
