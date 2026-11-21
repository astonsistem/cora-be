import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError
from app.models.branches import Branches
from app.models.companies import Companies
from app.models.customer_visits import CustomerVisits
from app.models.sources import Sources
from app.models.users import Users
from app.models.voucher import Vouchers
from app.models.voucher_qr import VoucherMode, VoucherQrs
from app.schemas.voucher_qr_schema import VoucherQrCreate
from app.services.base_service import CrudService
from app.services.category_guard import CategoryGuard
from app.services.code_generator import CodeGenerator
from app.services.company_scope import CompanyScope


class VoucherQrService(CrudService[VoucherQrs]):
    model = VoucherQrs
    label = "QR"
    invalid_reference_message = "Source, category, atau voucher tidak valid"
    MIN_MULTI_VOUCHERS = 2

    def __init__(self, db: Session, current_user: Users):
        super().__init__(db)
        self.user = current_user
        self.scope = CompanyScope(current_user)

    def _scoped(self, query):
        if self.scope.restricted:
            return query.where(VoucherQrs.company_id == self.scope.company_id)
        return query

    def get_all(self, skip: int = 0, limit: int = 100) -> list[VoucherQrs]:
        query = self._scoped(select(VoucherQrs)).order_by(VoucherQrs.created_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def get_by_id(self, obj_id) -> VoucherQrs | None:
        return self.db.scalar(self._scoped(select(VoucherQrs).where(VoucherQrs.qr_id == obj_id)))

    def _resolve_company(self, company_id: uuid.UUID | None) -> uuid.UUID:
        if self.scope.restricted:
            return self.scope.company_id
        if company_id is None:
            raise BadRequestError("company_id wajib diisi")
        if self.db.get(Companies, company_id) is None:
            raise BadRequestError("Company tidak ditemukan")
        return company_id

    def _ensure_branch(self, company_id: uuid.UUID, branch_id: uuid.UUID | None) -> None:
        if branch_id is None:
            return
        branch = self.db.get(Branches, branch_id)
        if branch is None or branch.company_id != company_id:
            raise BadRequestError("Branch bukan milik company QR ini")

    def _ensure_references(self, company_id: uuid.UUID, source_id, category_id) -> None:
        if source_id is not None and self.db.get(Sources, source_id) is None:
            raise BadRequestError("Source tidak ditemukan")
        CategoryGuard(self.db).ensure_in_company(category_id, company_id)

    def _ensure_vouchers(self, company_id: uuid.UUID, mode: str, voucher_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        unique_ids = list(dict.fromkeys(voucher_ids))
        if mode == VoucherMode.single.value and len(unique_ids) != 1:
            raise BadRequestError("Mode single hanya boleh memilih satu voucher")
        if mode != VoucherMode.single.value and len(unique_ids) < self.MIN_MULTI_VOUCHERS:
            raise BadRequestError("Mode ini membutuhkan minimal 2 voucher")
        found = self.db.scalar(
            select(func.count())
            .select_from(Vouchers)
            .where(Vouchers.voucher_id.in_(unique_ids), Vouchers.company_id == company_id)
        )
        if found != len(unique_ids):
            raise BadRequestError("Ada voucher yang bukan milik company QR ini")
        return unique_ids

    def _unique_code(self) -> str:
        generator = CodeGenerator.for_qr()
        for _ in range(10):
            code = generator.next()
            if self.db.scalar(select(VoucherQrs.qr_id).where(VoucherQrs.code == code)) is None:
                return code
        raise ConflictError("Gagal membuat kode QR, coba lagi")

    def _build(self, data: VoucherQrCreate) -> VoucherQrs:
        company_id = self._resolve_company(data.company_id)
        self._ensure_references(company_id, data.source_id, data.category_id)
        self._ensure_branch(company_id, data.branch_id)
        return VoucherQrs(
            company_id=company_id,
            branch_id=data.branch_id,
            name=data.name,
            source_id=data.source_id,
            category_id=data.category_id,
            voucher_mode=data.voucher_mode.value,
            voucher_ids=self._ensure_vouchers(company_id, data.voucher_mode.value, data.voucher_ids),
            is_active=data.is_active,
            code=self._unique_code(),
            created_by=self.user.user_id,
        )

    def _prepare_update(self, obj: VoucherQrs, values: dict) -> dict:
        for key in ("name", "source_id", "voucher_mode", "voucher_ids", "is_active"):
            if key in values and values[key] is None:
                values.pop(key)
        self._ensure_references(obj.company_id, values.get("source_id"), values.get("category_id"))
        self._ensure_branch(obj.company_id, values.get("branch_id"))
        if "voucher_mode" in values:
            values["voucher_mode"] = values["voucher_mode"].value
        mode = values.get("voucher_mode", obj.voucher_mode)
        voucher_ids = values.get("voucher_ids", obj.voucher_ids)
        values["voucher_ids"] = self._ensure_vouchers(obj.company_id, mode, voucher_ids)
        return values

    def regenerate_code(self, qr: VoucherQrs) -> VoucherQrs:
        qr.code = self._unique_code()
        self._commit()
        self.db.refresh(qr)
        return qr

    def delete(self, obj: VoucherQrs) -> None:
        used = self.db.scalar(
            select(func.count()).select_from(CustomerVisits).where(CustomerVisits.qr_id == obj.qr_id)
        )
        if used:
            raise ConflictError("QR sudah dipakai customer. Nonaktifkan saja, jangan dihapus")
        super().delete(obj)
