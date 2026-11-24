import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError
from app.models.category import Category
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers
from app.models.users import Users
from app.models.voucher import ClaimStatus, VoucherClaims, VoucherCodes
from app.models.voucher_qr import VoucherQrs
from app.services.category_service import CategoryService
from app.services.customer_service import CustomerService


class DataResetService:
    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.user = current_user

    def category_impact(self, company_id: uuid.UUID | None) -> dict:
        category_ids = self._category_ids(company_id)
        visit_ids = self._visit_ids_of_categories(category_ids)
        return {
            "categories": self._count(category_ids),
            "visits": self._count(visit_ids),
            "customers": self._count(select(Customers.customer_id).where(Customers.category_id.in_(category_ids))),
            "qrs": self._count(select(VoucherQrs.qr_id).where(VoucherQrs.category_id.in_(category_ids))),
            "claimed_visits": self._count(self._claimed_visit_ids(visit_ids)),
        }

    def reset_categories(self, company_id: uuid.UUID | None) -> dict:
        impact = self.category_impact(company_id)
        if impact["qrs"]:
            raise ConflictError(
                f"Category masih dipakai {impact['qrs']} QR. Ubah atau hapus QR tersebut dulu sebelum reset."
            )
        if impact["claimed_visits"]:
            raise ConflictError(
                f"{impact['claimed_visits']} customer visit sudah punya voucher yang diklaim atau ditukar, "
                "jadi category tidak bisa direset."
            )

        category_ids = self._category_ids(company_id)
        self._delete_visits(self._visit_ids_of_categories(category_ids))
        self.db.execute(update(Customers).where(Customers.category_id.in_(category_ids)).values(category_id=None))
        self.db.execute(delete(Category).where(Category.category_id.in_(category_ids)))
        self.db.commit()
        return impact

    def customer_impact(self, branch_id: uuid.UUID | None) -> dict:
        customer_ids = self._customer_ids(branch_id)
        return {
            "customers": self._count(customer_ids),
            "pending": self._count(customer_ids.where(Customers.asis_partner_id.is_(None))),
            "visits": self._count(select(CustomerVisits.visit_id).where(CustomerVisits.customer_id.in_(customer_ids))),
            "claimed_customers": self._count(self._claimed_customer_ids(customer_ids)),
        }

    def reset_customers(self, branch_id: uuid.UUID | None) -> dict:
        impact = self.customer_impact(branch_id)
        if impact["claimed_customers"]:
            raise ConflictError(
                f"{impact['claimed_customers']} customer sudah punya voucher yang diklaim atau ditukar, "
                "jadi customer tidak bisa direset."
            )

        customer_ids = self._customer_ids(branch_id)
        self.db.execute(update(VoucherCodes).where(VoucherCodes.customer_id.in_(customer_ids)).values(customer_id=None))
        self.db.execute(update(CustomerVisits).where(CustomerVisits.customer_id.in_(customer_ids)).values(customer_id=None))
        self.db.execute(delete(Customers).where(Customers.customer_id.in_(customer_ids)))
        self.db.commit()
        return impact

    def _category_ids(self, company_id: uuid.UUID | None):
        if self.user.is_superadmin and company_id is None:
            raise BadRequestError("company_id wajib diisi")
        return CategoryService._scoped(self.user, select(Category.category_id), company_id)

    def _customer_ids(self, branch_id: uuid.UUID | None):
        if self.user.is_superadmin and branch_id is None:
            raise BadRequestError("branch_id wajib diisi")
        query = CustomerService(self.db, self.user)._scope(select(Customers.customer_id))
        return query.where(Customers.branch_id == branch_id) if branch_id else query

    @staticmethod
    def _visit_ids_of_categories(category_ids):
        return select(CustomerVisits.visit_id).where(CustomerVisits.category_id.in_(category_ids))

    @staticmethod
    def _claimed_visit_ids(visit_ids):
        return (
            select(VoucherCodes.visit_id)
            .join(VoucherClaims, VoucherClaims.code_id == VoucherCodes.code_id)
            .where(VoucherCodes.visit_id.in_(visit_ids), VoucherClaims.status != ClaimStatus.cancelled.value)
            .distinct()
        )

    @staticmethod
    def _claimed_customer_ids(customer_ids):
        return (
            select(Customers.customer_id)
            .join(CustomerVisits, CustomerVisits.customer_id == Customers.customer_id, isouter=True)
            .join(VoucherCodes, (VoucherCodes.customer_id == Customers.customer_id) | (VoucherCodes.visit_id == CustomerVisits.visit_id))
            .join(VoucherClaims, VoucherClaims.code_id == VoucherCodes.code_id)
            .where(Customers.customer_id.in_(customer_ids), VoucherClaims.status != ClaimStatus.cancelled.value)
            .distinct()
        )

    def _delete_visits(self, visit_ids) -> None:
        code_ids = select(VoucherCodes.code_id).where(VoucherCodes.visit_id.in_(visit_ids))
        self.db.execute(delete(VoucherClaims).where(VoucherClaims.code_id.in_(code_ids)))
        self.db.execute(delete(VoucherCodes).where(VoucherCodes.visit_id.in_(visit_ids)))
        self.db.execute(delete(CustomerVisits).where(CustomerVisits.visit_id.in_(visit_ids)))

    def _count(self, query) -> int:
        return self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
