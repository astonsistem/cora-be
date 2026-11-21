import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.customer_visits import CustomerVisits
from app.models.users import Users
from app.models.voucher import ClaimChannel, ClaimStatus, VoucherClaims, VoucherCodes, Vouchers
from app.schemas.voucher_schema import ClaimCreate
from app.services.claim_customer import ClaimCustomerLinker, CustomerMatcher
from app.services.company_scope import CompanyScope
from app.services.voucher_redeem_service import VoucherRedeemService


class VoucherClaimService:
    def __init__(self, db: Session, current_user: Users, redeem: VoucherRedeemService | None = None):
        self.db = db
        self.user = current_user
        self.scope = CompanyScope(current_user)
        self.redeem = redeem or VoucherRedeemService(db)

    def _base_query(self):
        return (
            select(VoucherClaims)
            .join(VoucherCodes, VoucherCodes.code_id == VoucherClaims.code_id)
            .join(Vouchers, Vouchers.voucher_id == VoucherCodes.voucher_id)
            .join(CustomerVisits, CustomerVisits.visit_id == VoucherCodes.visit_id)
        )

    def _scoped(self, query):
        if self.user.is_superadmin:
            return query
        query = query.where(Vouchers.company_id == self.scope.company_id)
        if self.user.is_admin:
            return query
        if self.user.branch_id is None:
            raise ForbiddenError("Akun Anda belum terhubung ke branch")
        return query.where(VoucherClaims.branch_id == self.user.branch_id)

    def _filtered(self, status: ClaimStatus | None, search: str | None):
        query = self._scoped(self._base_query())
        if status:
            query = query.where(VoucherClaims.status == status.value)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    CustomerVisits.customer_name.ilike(pattern),
                    CustomerVisits.phone.ilike(pattern),
                    VoucherCodes.code.ilike(pattern),
                )
            )
        return query

    def get_all(self, skip: int = 0, limit: int = 100, status=None, search=None) -> list[VoucherClaims]:
        query = self._filtered(status, search).order_by(VoucherClaims.claimed_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_all(self, status=None, search=None) -> int:
        subquery = self._filtered(status, search).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def get_or_404(self, claim_id: uuid.UUID) -> VoucherClaims:
        claim = self.db.scalar(self._scoped(self._base_query()).where(VoucherClaims.claim_id == claim_id))
        if claim is None:
            raise NotFoundError("Data klaim tidak ditemukan")
        return claim

    @staticmethod
    def to_record(claim: VoucherClaims) -> dict:
        visit = claim.code_ref.visit
        return {
            "claim_id": claim.claim_id,
            "code": claim.code_ref.code,
            "customer_name": visit.customer_name,
            "customer_phone": visit.phone,
            "voucher_name": claim.code_ref.voucher.voucher_name,
            "branch_name": claim.branch.branch_name,
            "claimed_at": claim.claimed_at,
            "redeemed_at": claim.redeemed_at,
            "cancelled_at": claim.cancelled_at,
            "redeemed_by": claim.redeemed_by,
            "redeemed_by_name": VoucherClaimService._full_name(claim.redeemer),
            "status": claim.status,
            "flag_reason": claim.flag_reason,
        }

    @staticmethod
    def _full_name(user: Users | None) -> str | None:
        return f"{user.first_name} {user.last_name}".strip() if user else None

    def _resolve_branch(self, branch_id: uuid.UUID | None) -> uuid.UUID:
        if self.user.is_admin:
            if branch_id is None:
                raise BadRequestError("branch_id wajib diisi")
            return branch_id
        if self.user.branch_id is None:
            raise ForbiddenError("Akun Anda belum terhubung ke branch")
        if branch_id is not None and branch_id != self.user.branch_id:
            raise ForbiddenError("Anda hanya boleh memakai branch Anda sendiri")
        return self.user.branch_id

    def _code_in_scope(self, code: str) -> VoucherCodes:
        record = self.redeem.get_code(code)
        if not self.user.is_superadmin and record.voucher.company_id != self.scope.company_id:
            raise NotFoundError("Kode voucher tidak ditemukan.")
        return record

    def create(self, data: ClaimCreate) -> VoucherClaims:
        record = self._code_in_scope(data.code)
        claim = self.redeem.create_claim(record, self._resolve_branch(data.branch_id), ClaimChannel.staff)
        if data.redeem:
            self._mark_redeemed(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def approve(self, claim_id: uuid.UUID) -> VoucherClaims:
        claim = self.get_or_404(claim_id)
        self._mark_redeemed(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def _mark_redeemed(self, claim: VoucherClaims) -> None:
        if claim.status != ClaimStatus.claimed.value:
            raise ConflictError("Hanya klaim berstatus CLAIMED yang bisa ditandai sudah digunakan")
        if claim.is_flagged and not self.user.is_admin:
            raise ForbiddenError("Klaim ini ditandai dan harus diperiksa OM atau Superadmin")
        claim.status = ClaimStatus.redeemed.value
        claim.redeemed_at = datetime.now()
        claim.redeemed_by = self.user.user_id
        company_id = claim.code_ref.voucher.company_id
        ClaimCustomerLinker(self.db, CustomerMatcher(self.db, company_id)).link(claim, self.user.user_id)

    def clear_flag(self, claim_id: uuid.UUID) -> VoucherClaims:
        claim = self.get_or_404(claim_id)
        claim.flag_reason = None
        self.db.commit()
        self.db.refresh(claim)
        return claim
