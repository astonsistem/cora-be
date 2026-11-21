import random
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.customer_visits import CustomerVisits
from app.models.voucher import VoucherCodes, Vouchers
from app.models.voucher_qr import VoucherMode
from app.services.code_generator import CodeGenerator
from app.services.voucher_availability import VoucherAvailability


class VoucherIssueService:
    MAX_CODE_ATTEMPTS = 10

    def __init__(self, db: Session, availability: VoucherAvailability | None = None):
        self.db = db
        self.availability = availability or VoucherAvailability()
        self.generator = CodeGenerator.for_voucher_code()

    def _visit(self, token: str) -> CustomerVisits:
        visit = self.db.scalar(select(CustomerVisits).where(CustomerVisits.claim_token == token))
        if visit is None:
            raise NotFoundError("Sesi claim tidak valid. Silakan isi data kembali.")
        if visit.claim_expires_at is None or visit.claim_expires_at < datetime.now():
            raise ConflictError("Sesi claim sudah berakhir. Silakan scan QR kembali.")
        return visit

    def _available(self, visit: CustomerVisits) -> list[Vouchers]:
        qr = visit.qr
        query = (
            select(Vouchers)
            .where(
                Vouchers.voucher_id.in_(qr.voucher_ids),
                Vouchers.company_id == qr.company_id,
                *self.availability.conditions(),
            )
            .order_by(Vouchers.voucher_name)
        )
        return list(self.db.scalars(query))

    def _issued(self, visit: CustomerVisits) -> list[VoucherCodes]:
        return list(
            self.db.scalars(
                select(VoucherCodes).where(VoucherCodes.visit_id == visit.visit_id).order_by(VoucherCodes.issued_at)
            )
        )

    def _pick(self, mode: str, vouchers: list[Vouchers]) -> list[Vouchers]:
        if mode == VoucherMode.all.value:
            return vouchers
        if mode == VoucherMode.random_one.value:
            return [random.choice(vouchers)]
        return vouchers[:1]

    def _issue_code(self, voucher: Vouchers, visit: CustomerVisits) -> VoucherCodes | None:
        if not self.availability.take_one(self.db, voucher.voucher_id):
            return None
        for _ in range(self.MAX_CODE_ATTEMPTS):
            code = VoucherCodes(code=self.generator.next(), voucher_id=voucher.voucher_id, visit_id=visit.visit_id)
            try:
                with self.db.begin_nested():
                    self.db.add(code)
                return code
            except IntegrityError:
                continue
        raise ConflictError("Gagal membuat kode voucher, coba lagi")

    def _claim_chosen(self, visit: CustomerVisits, voucher_id: uuid.UUID) -> VoucherCodes:
        qr = visit.qr
        if voucher_id not in qr.voucher_ids:
            raise NotFoundError("Voucher tidak ditemukan.")
        issued = self._issued(visit)
        for code in issued:
            if code.voucher_id == voucher_id:
                return code

        voucher = self.db.scalar(
            select(Vouchers).where(Vouchers.voucher_id == voucher_id, Vouchers.company_id == qr.company_id)
        )
        if voucher is None:
            raise NotFoundError("Voucher tidak ditemukan.")
        if self.availability.is_expired(voucher):
            raise ConflictError("Voucher sudah kedaluwarsa.")

        code = self._issue_code(voucher, visit)
        if code is None:
            self.db.rollback()
            raise ConflictError("Voucher sedang tidak tersedia.")
        visit.meta = {**visit.meta, "voucher_codes": [*visit.meta.get("voucher_codes", []), code.code]}
        self.db.commit()
        return code

    def claim(self, token: str, voucher_id: uuid.UUID | None = None) -> list[VoucherCodes]:
        visit = self._visit(token)
        if voucher_id is not None:
            return [self._claim_chosen(visit, voucher_id)]

        existing = self._issued(visit)
        if existing:
            return existing

        vouchers = self._available(visit)
        if not vouchers:
            raise ConflictError("Voucher sedang tidak tersedia")

        issued = [
            code
            for voucher in self._pick(visit.qr.voucher_mode, vouchers)
            if (code := self._issue_code(voucher, visit)) is not None
        ]
        if not issued:
            self.db.rollback()
            raise ConflictError("Voucher sedang tidak tersedia")

        visit.meta = {**visit.meta, "voucher_codes": [code.code for code in issued]}
        self.db.commit()
        return issued
