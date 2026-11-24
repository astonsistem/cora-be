import uuid
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.branches import Branches
from app.models.companies import Companies
from app.models.users import Users
from app.models.voucher import VoucherCodes, Vouchers, VoucherStatus
from app.models.voucher_qr import VoucherQrs
from app.schemas.voucher_schema import VoucherCreate, VoucherUpdate
from app.services.code_generator import CodeGenerator
from app.services.company_scope import CompanyScope


class VoucherService:
    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.user = current_user
        self.scope = CompanyScope(current_user)

    def _scoped(self, query):
        if self.scope.restricted:
            return query.where(Vouchers.company_id == self.scope.company_id)
        return query

    def _resolve_company(self, company_id: uuid.UUID | None) -> uuid.UUID:
        if self.scope.restricted:
            return self.scope.company_id
        if company_id is None:
            raise BadRequestError("company_id wajib diisi")
        if self.db.get(Companies, company_id) is None:
            raise BadRequestError("Company tidak ditemukan")
        return company_id

    def _validated_branch_ids(self, company_id: uuid.UUID, branch_ids: list[uuid.UUID] | None):
        if not branch_ids:
            return None
        unique_ids = list(dict.fromkeys(branch_ids))
        found = self.db.scalar(
            select(func.count())
            .select_from(Branches)
            .where(Branches.branch_id.in_(unique_ids), Branches.company_id == company_id)
        )
        if found != len(unique_ids):
            raise BadRequestError("Ada branch yang bukan milik company voucher ini")
        return unique_ids

    def _unique_value(self, generator: CodeGenerator, column) -> str:
        for _ in range(10):
            value = generator.next()
            if self.db.scalar(select(Vouchers.voucher_id).where(column == value)) is None:
                return value
        raise ConflictError("Gagal membuat kode unik, coba lagi")

    def _commit(self, message: str) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(message)

    def get_or_404(self, voucher_id: uuid.UUID) -> Vouchers:
        voucher = self.db.scalar(
            self._scoped(select(Vouchers).where(Vouchers.voucher_id == voucher_id, Vouchers.archived_at.is_(None)))
        )
        if voucher is None:
            raise NotFoundError("Voucher tidak ditemukan")
        return voucher

    def get_archived_or_404(self, voucher_id: uuid.UUID) -> Vouchers:
        voucher = self.db.scalar(
            self._scoped(select(Vouchers).where(Vouchers.voucher_id == voucher_id, Vouchers.archived_at.isnot(None)))
        )
        if voucher is None:
            raise NotFoundError("Voucher tidak ada di arsip")
        return voucher

    def archive(self, voucher: Vouchers) -> Vouchers:
        voucher.archived_at = datetime.now()
        voucher.status = VoucherStatus.inactive.value
        self._commit("Voucher tidak dapat diarsipkan")
        self.db.refresh(voucher)
        return voucher

    def unarchive(self, voucher: Vouchers) -> Vouchers:
        if voucher.date_expired < date.today():
            raise ConflictError(
                "Voucher sudah kedaluwarsa, jadi tidak bisa dikeluarkan dari arsip. Buat voucher baru."
            )
        if voucher.used_count >= voucher.quota_voucher:
            raise ConflictError(
                "Kuota voucher sudah habis, jadi tidak bisa dikeluarkan dari arsip. Buat voucher baru."
            )
        voucher.archived_at = None
        voucher.status = VoucherStatus.active.value
        self._commit("Voucher tidak dapat dikeluarkan dari arsip")
        self.db.refresh(voucher)
        return voucher

    def _list_query(self, status: str | None, company_id: uuid.UUID | None):
        query = self._scoped(select(Vouchers)).where(Vouchers.archived_at.is_(None))
        if status:
            query = query.where(Vouchers.status == status)
        if company_id and not self.scope.restricted:
            query = query.where(Vouchers.company_id == company_id)
        return query

    def get_all(self, skip: int = 0, limit: int = 100, status=None, company_id=None) -> list[Vouchers]:
        query = self._list_query(status, company_id).order_by(Vouchers.created_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_all(self, status=None, company_id=None) -> int:
        subquery = self._list_query(status, company_id).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def _archived_query(self, search: str | None):
        query = self._scoped(select(Vouchers)).where(Vouchers.archived_at.isnot(None))
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(or_(Vouchers.voucher_name.ilike(pattern), Vouchers.code.ilike(pattern)))
        return query

    def get_archived(self, skip: int = 0, limit: int = 100, search: str | None = None) -> list[Vouchers]:
        query = self._archived_query(search).order_by(Vouchers.archived_at.desc(), Vouchers.voucher_name)
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def count_archived(self, search: str | None = None) -> int:
        subquery = self._archived_query(search).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def create(self, data: VoucherCreate) -> Vouchers:
        company_id = self._resolve_company(data.company_id)
        code = (data.code or "").strip().upper() or self._unique_value(
            CodeGenerator.for_voucher_definition(), Vouchers.code
        )
        voucher = Vouchers(
            **data.model_dump(exclude={"company_id", "code", "branch_ids", "status"}),
            status=data.status.value,
            company_id=company_id,
            code=code,
            branch_ids=self._validated_branch_ids(company_id, data.branch_ids),
            qr_slug=self._unique_value(CodeGenerator.for_qr(), Vouchers.qr_slug),
            created_by=self.user.user_id,
        )
        self.db.add(voucher)
        self._commit("Kode atau nama voucher sudah dipakai di company ini")
        self.db.refresh(voucher)
        return voucher

    def update_design(self, voucher: Vouchers, design: dict | None) -> Vouchers:
        voucher.design = design
        self._commit("Desain voucher tidak dapat disimpan")
        self.db.refresh(voucher)
        return voucher

    def update(self, voucher: Vouchers, data: VoucherUpdate) -> Vouchers:
        values = data.model_dump(exclude_unset=True)
        for key in ("voucher_name", "quota_voucher", "status", "date_started", "date_expired"):
            if key in values and values[key] is None:
                values.pop(key)

        if "quota_voucher" in values and values["quota_voucher"] < voucher.used_count:
            raise BadRequestError("Kuota tidak boleh lebih kecil dari voucher yang sudah diklaim")

        date_started = values.get("date_started", voucher.date_started)
        date_expired = values.get("date_expired", voucher.date_expired)
        if date_expired < date_started:
            raise BadRequestError("date_expired tidak boleh lebih awal dari date_started")

        if "branch_ids" in values:
            values["branch_ids"] = self._validated_branch_ids(voucher.company_id, values["branch_ids"])
        if "status" in values:
            values["status"] = values["status"].value
        if values.get("qr_target_id") is not None:
            self._ensure_qr_in_company(voucher.company_id, values["qr_target_id"])

        for key, value in values.items():
            setattr(voucher, key, value)
        self._sync_sold_out(voucher)
        self._commit("Nama voucher sudah dipakai di company ini")
        self.db.refresh(voucher)
        return voucher

    @staticmethod
    def _sync_sold_out(voucher: Vouchers) -> None:
        if voucher.used_count > 0 and voucher.used_count >= voucher.quota_voucher:
            voucher.sold_out_at = voucher.sold_out_at or datetime.now()
        else:
            voucher.sold_out_at = None

    def _ensure_qr_in_company(self, company_id: uuid.UUID, qr_id: uuid.UUID) -> None:
        qr = self.db.get(VoucherQrs, qr_id)
        if qr is None or qr.company_id != company_id:
            raise BadRequestError("QR tujuan tidak valid untuk company ini")

    def delete(self, voucher: Vouchers) -> None:
        issued = self.db.scalar(
            select(func.count()).select_from(VoucherCodes).where(VoucherCodes.voucher_id == voucher.voucher_id)
        )
        if issued:
            raise ConflictError("Voucher sudah pernah diklaim. Nonaktifkan saja, jangan dihapus")
        self.db.delete(voucher)
        self.db.commit()
