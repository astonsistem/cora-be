import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.branches import Branches
from app.models.voucher import ClaimChannel, ClaimStatus, VoucherClaims, VoucherCodes, Vouchers
from app.services.claim_customer import ClaimFlagDetector, CustomerMatcher
from app.services.voucher_availability import VoucherAvailability


class VoucherRedeemService:
    def __init__(self, db: Session, availability: VoucherAvailability | None = None):
        self.db = db
        self.availability = availability or VoucherAvailability()

    def get_code(self, code: str) -> VoucherCodes:
        record = self.db.scalar(select(VoucherCodes).where(VoucherCodes.code == code.strip().upper()))
        if record is None:
            raise NotFoundError("Kode voucher tidak ditemukan.")
        return record

    def allowed_branches(self, record: VoucherCodes) -> list[Branches]:
        voucher = record.voucher
        query = select(Branches).where(Branches.company_id == voucher.company_id, Branches.deleted_at.is_(None))
        if voucher.branch_ids:
            query = query.where(Branches.branch_id.in_(voucher.branch_ids))
        qr = record.visit.qr
        if qr is not None and qr.branch_id is not None:
            query = query.where(Branches.branch_id == qr.branch_id)
        return list(self.db.scalars(query.order_by(Branches.branch_name)))

    def view(self, code: str) -> dict:
        record = self.get_code(code)
        voucher = record.voucher
        claims = [self._history_item(claim) for claim in record.claims]
        active = record.active_claim
        return {
            "code": record.code,
            "voucher_name": voucher.voucher_name,
            "date_expired": voucher.date_expired,
            "expired": self.availability.is_expired(voucher),
            "customer_name": record.visit.customer_name,
            "branches": self.allowed_branches(record),
            "claims": claims,
            "active_claim": self._history_item(active) if active else None,
        }

    @staticmethod
    def _history_item(claim: VoucherClaims) -> dict:
        return {
            "claim_id": claim.claim_id,
            "branch_id": claim.branch_id,
            "branch_name": claim.branch.branch_name,
            "status": claim.status,
            "claimed_at": claim.claimed_at,
            "redeemed_at": claim.redeemed_at,
            "cancelled_at": claim.cancelled_at,
        }

    def _ensure_claimable(self, record: VoucherCodes, branch_id: uuid.UUID) -> None:
        voucher = record.voucher
        if self.availability.is_expired(voucher):
            raise ConflictError("Voucher ini sudah kedaluwarsa.")
        active = record.active_claim
        if active is not None and active.status == ClaimStatus.redeemed.value:
            raise ConflictError("Voucher ini sudah digunakan.")
        if active is not None:
            raise ConflictError(
                f"Voucher ini sudah diklaim di {active.branch.branch_name}. "
                "Batalkan klaim terlebih dahulu untuk pindah outlet."
            )
        if branch_id not in {branch.branch_id for branch in self.allowed_branches(record)}:
            raise BadRequestError("Outlet tidak tersedia untuk voucher ini.")

    def create_claim(self, record: VoucherCodes, branch_id: uuid.UUID, channel: ClaimChannel) -> VoucherClaims:
        self._ensure_claimable(record, branch_id)
        flag = ClaimFlagDetector(CustomerMatcher(self.db, record.voucher.company_id)).detect(record.visit)
        claim = VoucherClaims(
            code_id=record.code_id,
            branch_id=branch_id,
            status=ClaimStatus.claimed.value,
            claimed_via=channel.value,
            flag_reason=flag.value if flag else None,
        )
        try:
            with self.db.begin_nested():
                self.db.add(claim)
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Voucher ini sudah memiliki klaim aktif.")
        return claim

    def claim(self, code: str, branch_id: uuid.UUID) -> dict:
        record = self.get_code(code)
        self.create_claim(record, branch_id, ClaimChannel.customer)
        self.db.commit()
        self.db.refresh(record)
        return self.view(record.code)

    def cancel(self, code: str, claim_id: uuid.UUID) -> dict:
        record = self.get_code(code)
        claim = next((item for item in record.claims if item.claim_id == claim_id), None)
        if claim is None:
            raise NotFoundError("Data klaim tidak ditemukan.")
        if claim.status == ClaimStatus.redeemed.value:
            raise ConflictError("Voucher yang sudah digunakan tidak dapat dibatalkan.")
        if claim.status == ClaimStatus.cancelled.value:
            raise ConflictError("Klaim ini sudah dibatalkan.")
        claim.status = ClaimStatus.cancelled.value
        claim.cancelled_at = datetime.now()
        self.db.commit()
        self.db.refresh(record)
        return self.view(record.code)
