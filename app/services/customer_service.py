import uuid

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.branches import Branches
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match
from app.models.users import UserRole, Users
from app.schemas.customer_schema import CustomerCreate
from app.services.base_service import CrudService

class DuplicateCustomerError(ConflictError):
    def __init__(self, customer: Customers):
        super().__init__(f"Customer '{customer.name}' sudah ada di Master Customer")
        self.customer = customer

class CustomerPostedError(ConflictError):
    """Customer yang sudah diposting ke ASIS tidak boleh diubah atau dihapus dari CORA."""

class CustomerService(CrudService[Customers]):
    """Master Customer. Semua query dibatasi oleh cakupan user yang sedang login."""

    model = Customers
    label = "Customer"
    invalid_reference_message = "Invalid category or branch reference"
    in_use_message = "Customer masih dipakai oleh customer visit"

    def __init__(self, db: Session, current_user: Users):
        super().__init__(db)
        self.user = current_user

    def _scope(self, query):
        if self.user.user_role == UserRole.operasional_manager:
            if self.user.company_id is None:
                return query
            return query.join(Branches, Customers.branch_id == Branches.branch_id).where(
                Branches.company_id == self.user.company_id
            )
        if self.user.branch_id is None:
            return query.where(false())
        return query.where(Customers.branch_id == self.user.branch_id)

    def _filtered(
        self,
        q: str | None = None,
        status: str | None = None,
        branch_id: uuid.UUID | None = None,
        deleted: bool = False,
    ):
        query = self._scope(select(Customers))
        query = query.where(Customers.deleted_at.isnot(None) if deleted else Customers.deleted_at.is_(None))
        if branch_id:
            query = query.where(Customers.branch_id == branch_id)
        if status == "posted":
            query = query.where(Customers.asis_partner_id.isnot(None))
        elif status == "pending":
            query = query.where(Customers.asis_partner_id.is_(None))
        if q and q.strip():
            conditions = [
                Customers.name_search.contains(normalize_name(q), autoescape=True),
                Customers.email.icontains(q.strip(), autoescape=True),
            ]
            digits = normalize_phone(q)
            if len(digits) >= 3:
                conditions.append(Customers.phone_norm.contains(digits, autoescape=True))
            query = query.where(or_(*conditions))
        return query

    def get_by_id(self, obj_id, deleted: bool = False) -> Customers | None:
        query = self._scope(select(Customers).where(Customers.customer_id == obj_id))
        query = query.where(Customers.deleted_at.isnot(None) if deleted else Customers.deleted_at.is_(None))
        return self.db.scalar(query)

    def get_deleted_or_404(self, obj_id) -> Customers:
        customer = self.get_by_id(obj_id, deleted=True)
        if customer is None:
            raise NotFoundError("Customer yang dihapus tidak ditemukan")
        return customer

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        q: str | None = None,
        status: str | None = None,
        branch_id: uuid.UUID | None = None,
        deleted: bool = False,
    ) -> list[Customers]:
        query = self._filtered(q, status, branch_id, deleted)
        order = (Customers.deleted_at.desc(), Customers.name_search) if deleted else (Customers.name_search,)
        query = query.order_by(*order).offset(skip).limit(min(max(limit, 1), 200))
        return list(self.db.scalars(query))

    def count_all(
        self,
        q: str | None = None,
        status: str | None = None,
        branch_id: uuid.UUID | None = None,
        deleted: bool = False,
    ) -> int:
        subquery = self._filtered(q, status, branch_id, deleted).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def find_duplicate(
        self,
        branch_id: uuid.UUID,
        name: str,
        phone: str | None,
        exclude_id: uuid.UUID | None = None,
    ) -> Customers | None:
        query = select(Customers).where(
            Customers.branch_id == branch_id,
            Customers.name_search == normalize_name(name),
            Customers.deleted_at.is_(None),
        )
        if exclude_id:
            query = query.where(Customers.customer_id != exclude_id)
        phone_norm = normalize_phone(phone) or None
        for customer in self.db.scalars(query):
            if phones_match(customer.phone_norm, phone_norm):
                return customer
        return None

    def _resolve_branch(self, branch_id: uuid.UUID | None) -> Branches:
        if self.user.user_role == UserRole.operasional_manager:
            if branch_id is None:
                raise BadRequestError("branch_id wajib diisi oleh Operasional Manager")
            branch = self.db.get(Branches, branch_id)
            if branch is None:
                raise BadRequestError("Branch tidak ditemukan")
            if self.user.company_id is not None and branch.company_id != self.user.company_id:
                raise ForbiddenError("Branch tersebut bukan milik company Anda")
            return branch

        if self.user.branch_id is None:
            raise BadRequestError("Branch Anda belum diatur, hubungi admin")
        if branch_id is not None and branch_id != self.user.branch_id:
            raise ForbiddenError("Anda hanya boleh memakai branch Anda sendiri")
        return self.db.get(Branches, self.user.branch_id)

    def _build(self, data: CustomerCreate) -> Customers:
        branch = self._resolve_branch(data.branch_id)
        duplicate = self.find_duplicate(branch.branch_id, data.name, data.phone)
        if duplicate:
            raise DuplicateCustomerError(duplicate)

        return Customers(
            name=data.name,
            phone=data.phone,
            email=data.email,
            category_id=data.category_id,
            branch_id=branch.branch_id,
            created_by=self.user.user_id,
        )

    def _prepare_update(self, customer: Customers, values: dict) -> dict:
        if customer.is_posted:
            raise CustomerPostedError("Customer yang sudah diposting ke ASIS tidak dapat diubah")

        if values.get("name") is None:
            values.pop("name", None)
        if "branch_id" in values:
            branch_id = values.pop("branch_id")
            if branch_id is not None and branch_id != customer.branch_id:
                customer.branch_id = self._resolve_branch(branch_id).branch_id

        new_name = values.get("name", customer.name)
        new_phone = values["phone"] if "phone" in values else customer.phone
        duplicate = self.find_duplicate(
            customer.branch_id, new_name, new_phone, exclude_id=customer.customer_id
        )
        if duplicate:
            raise DuplicateCustomerError(duplicate)

        return values

    def delete(self, customer: Customers) -> None:
        customer.soft_delete()
        self._commit()

    def restore(self, customer: Customers) -> Customers:
        duplicate = self.find_duplicate(
            customer.branch_id, customer.name, customer.phone, exclude_id=customer.customer_id
        )
        if duplicate:
            raise DuplicateCustomerError(duplicate)
        customer.restore()
        self._commit()
        self.db.refresh(customer)
        return customer

    def ensure_customer(
        self,
        name: str,
        phone: str | None,
        category_id: uuid.UUID | None,
        branch_id: uuid.UUID | None,
    ) -> Customers:
        name = (name or "").strip()
        phone = (phone or "").strip() or None
        if not name:
            raise BadRequestError("Nama customer wajib diisi")

        branch = self._resolve_branch(branch_id)
        existing = self.find_duplicate(branch.branch_id, name, phone)
        if existing:
            return existing

        customer = Customers(
            name=name,
            phone=phone,
            category_id=category_id,
            branch_id=branch.branch_id,
            created_by=self.user.user_id,
        )
        self.db.add(customer)
        self.db.flush()
        return customer

    def create_from_visit(self, visit: CustomerVisits) -> Customers:
        branch = visit.user.branch if visit.user else None
        if branch is None:
            raise BadRequestError("User pembuat visit belum punya branch")

        existing = self.find_duplicate(branch.branch_id, visit.customer_name, visit.phone)
        if existing:
            return existing

        customer = Customers(
            name=visit.customer_name,
            phone=visit.phone,
            category_id=visit.category_id,
            branch_id=branch.branch_id,
            created_by=visit.user_id,
        )
        self.db.add(customer)
        self.db.flush()
        return customer
