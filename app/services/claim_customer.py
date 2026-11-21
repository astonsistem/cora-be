import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branches import Branches
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers, normalize_name, normalize_phone
from app.models.voucher import ClaimFlag, VoucherClaims, VoucherCodes
from app.models.voucher_qr import VoucherQrs


class CustomerMatcher:
    def __init__(self, db: Session, company_id: uuid.UUID):
        self.db = db
        self.company_id = company_id

    def by_phone(self, phone: str | None) -> list[Customers]:
        phone_norm = normalize_phone(phone)
        if not phone_norm:
            return []
        query = (
            select(Customers)
            .join(Branches, Branches.branch_id == Customers.branch_id)
            .where(
                Branches.company_id == self.company_id,
                Customers.phone_norm == phone_norm,
                Customers.deleted_at.is_(None),
            )
            .order_by(Customers.created_at)
        )
        return list(self.db.scalars(query))


class ClaimFlagDetector:
    def __init__(self, matcher: CustomerMatcher):
        self.matcher = matcher

    def detect(self, visit: CustomerVisits) -> ClaimFlag | None:
        if visit.customer_id is not None:
            return None
        matches = self.matcher.by_phone(visit.phone)
        if len(matches) > 1:
            return ClaimFlag.multiple_match
        if matches and matches[0].name_search != normalize_name(visit.customer_name):
            return ClaimFlag.phone_name_mismatch
        return None


class VisitCustomerRegistrar:
    def __init__(self, db: Session):
        self.db = db

    def register(self, visit: CustomerVisits, qr: VoucherQrs) -> Customers | None:
        if CustomerMatcher(self.db, qr.company_id).by_phone(visit.phone):
            return None
        branch_id = self._branch_id(qr)
        if branch_id is None:
            return None
        customer = Customers(
            name=visit.customer_name,
            phone=visit.phone,
            category_id=visit.category_id,
            branch_id=branch_id,
        )
        self.db.add(customer)
        self.db.flush()
        visit.customer_id = customer.customer_id
        return customer

    def _branch_id(self, qr: VoucherQrs) -> uuid.UUID | None:
        if qr.branch_id is not None:
            return qr.branch_id
        branch_ids = list(
            self.db.scalars(select(Branches.branch_id).where(Branches.company_id == qr.company_id).limit(2))
        )
        return branch_ids[0] if len(branch_ids) == 1 else None


class ClaimCustomerLinker:
    def __init__(self, db: Session, matcher: CustomerMatcher):
        self.db = db
        self.matcher = matcher

    def link(self, claim: VoucherClaims, created_by: uuid.UUID | None) -> Customers:
        visit = claim.code_ref.visit
        customer = self._existing(visit) or self._create(visit, claim, created_by)
        self._attach(visit, customer)
        return customer

    def _existing(self, visit: CustomerVisits) -> Customers | None:
        if visit.customer_id is not None:
            return self.db.get(Customers, visit.customer_id)
        matches = self.matcher.by_phone(visit.phone)
        return matches[0] if matches else None

    def _create(self, visit: CustomerVisits, claim: VoucherClaims, created_by: uuid.UUID | None) -> Customers:
        customer = Customers(
            name=visit.customer_name,
            phone=visit.phone,
            category_id=visit.category_id,
            branch_id=claim.branch_id,
            created_by=created_by,
        )
        self.db.add(customer)
        self.db.flush()
        return customer

    def _attach(self, visit: CustomerVisits, customer: Customers) -> None:
        visit.customer_id = customer.customer_id
        for code in self.db.scalars(select(VoucherCodes).where(VoucherCodes.visit_id == visit.visit_id)):
            code.customer_id = customer.customer_id
