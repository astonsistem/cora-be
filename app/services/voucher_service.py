import uuid
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError
from app.models.users import Users
from app.models.voucher import VoucherRedemptions, Vouchers
from app.schemas.voucher_schema import RedemptionStatus, VoucherCreate, VoucherUpdate


class VoucherService:
    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.user = current_user

    # ---------- scope ----------
    def _scope(self, query):
        """Branch Manager hanya melihat cabangnya; OM (tanpa branch_id) melihat semua."""
        if self.user.branch_id:
            query = query.where(Vouchers.branch_id == self.user.branch_id)
        return query

    def _resolve_branch(self, branch_id: uuid.UUID | None) -> uuid.UUID:
        if self.user.branch_id:
            return self.user.branch_id
        if branch_id is None:
            raise BadRequestError("branch_id wajib diisi")
        return branch_id

    def _commit(self, conflict_message: str) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(409, conflict_message)

    # ---------- voucher ----------
    def get_or_404(self, voucher_id: uuid.UUID) -> Vouchers:
        voucher = self.db.scalar(
            self._scope(select(Vouchers).where(Vouchers.voucher_id == voucher_id))
        )
        if voucher is None:
            raise HTTPException(404, "Voucher tidak ditemukan")
        return voucher

    def _list_query(self, is_active: bool | None, branch_id: uuid.UUID | None):
        query = self._scope(select(Vouchers))
        if is_active is not None:
            query = query.where(Vouchers.is_active.is_(is_active))
        if branch_id and not self.user.branch_id:
            query = query.where(Vouchers.branch_id == branch_id)
        return query

    def get_all(self, skip=0, limit=100, is_active=None, branch_id=None) -> list[Vouchers]:
        query = self._list_query(is_active, branch_id).order_by(Vouchers.created_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_all(self, is_active=None, branch_id=None) -> int:
        subquery = self._list_query(is_active, branch_id).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def create(self, data: VoucherCreate) -> Vouchers:
        voucher = Vouchers(
            **data.model_dump(exclude={"branch_id"}),
            branch_id=self._resolve_branch(data.branch_id),
            created_by=self.user.user_id,
        )
        self.db.add(voucher)
        self._commit("Voucher dengan nama ini sudah ada di cabang tersebut, atau cabang tidak valid")
        self.db.refresh(voucher)
        return voucher

    def update(self, voucher: Vouchers, data: VoucherUpdate) -> Vouchers:
        values = data.model_dump(exclude_unset=True)
        for key in ("name", "quota", "is_active"):  # kolom wajib tidak boleh dikosongkan
            if key in values and values[key] is None:
                values.pop(key)

        if "quota" in values and values["quota"] < voucher.used_count:
            raise BadRequestError("Kuota tidak boleh lebih kecil dari voucher yang sudah ditukar")

        valid_from = values.get("valid_from", voucher.valid_from)
        valid_until = values.get("valid_until", voucher.valid_until)
        if valid_from and valid_until and valid_until < valid_from:
            raise BadRequestError("valid_until tidak boleh lebih awal dari valid_from")

        for key, value in values.items():
            setattr(voucher, key, value)
        self._commit("Voucher dengan nama ini sudah ada di cabang tersebut")
        self.db.refresh(voucher)
        return voucher

    def delete(self, voucher: Vouchers) -> None:
        total = self.db.scalar(
            select(func.count())
            .select_from(VoucherRedemptions)
            .where(VoucherRedemptions.voucher_id == voucher.voucher_id)
        ) or 0
        if total:
            raise BadRequestError("Voucher sudah memiliki penukaran. Nonaktifkan saja, jangan dihapus")
        self.db.delete(voucher)
        self.db.commit()

    # ---------- penukaran ----------
    def _redemption_query(self, voucher_id, status, search, date_from, date_to):
        query = self._scope(
            select(VoucherRedemptions).join(
                Vouchers, Vouchers.voucher_id == VoucherRedemptions.voucher_id
            )
        )
        if voucher_id:
            query = query.where(VoucherRedemptions.voucher_id == voucher_id)
        if status:
            query = query.where(VoucherRedemptions.status == status.value)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    VoucherRedemptions.full_name.ilike(pattern),
                    VoucherRedemptions.phone.ilike(pattern),
                    VoucherRedemptions.phone_norm.ilike(pattern),
                )
            )
        if date_from:
            query = query.where(
                VoucherRedemptions.submitted_at >= datetime.combine(date_from, time.min)
            )
        if date_to:
            query = query.where(
                VoucherRedemptions.submitted_at
                < datetime.combine(date_to + timedelta(days=1), time.min)
            )
        return query

    def get_redemptions(
        self,
        skip: int = 0,
        limit: int = 100,
        voucher_id: uuid.UUID | None = None,
        status: RedemptionStatus | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[VoucherRedemptions]:
        query = self._redemption_query(voucher_id, status, search, date_from, date_to)
        query = query.order_by(VoucherRedemptions.submitted_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_redemptions(
        self, voucher_id=None, status=None, search=None, date_from=None, date_to=None
    ) -> int:
        subquery = self._redemption_query(voucher_id, status, search, date_from, date_to).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def update_redemption_status(
        self, redemption_id: uuid.UUID, status: RedemptionStatus
    ) -> VoucherRedemptions:
        redemption = self.db.scalar(
            self._scope(
                select(VoucherRedemptions)
                .join(Vouchers, Vouchers.voucher_id == VoucherRedemptions.voucher_id)
                .where(VoucherRedemptions.redemption_id == redemption_id)
            )
        )
        if redemption is None:
            raise HTTPException(404, "Data penukaran tidak ditemukan")
        redemption.status = status.value
        self.db.commit()
        self.db.refresh(redemption)
        return redemption