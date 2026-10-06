import uuid

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from app.models.branches import Branches
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match
from app.models.users import UserRole, Users
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate


class DuplicateCustomerError(ValueError):
    def __init__(self, customer: Customers):
        super().__init__(f"Customer '{customer.name}' sudah ada di Master Customer")
        self.customer = customer

class CustomerPostedError(ValueError):
    """Customer yang sudah diposting ke ASIS tidak boleh diubah atau dihapus dari CORA."""

def scoped(query, user: Users):
    if user.user_role == UserRole.operasional_manager:
        if user.company_id is None:
            return query
        return query.join(Branches, Customers.branch_id == Branches.branch_id).where(
            Branches.company_id == user.company_id
        )
    if user.branch_id is None:
        return query.where(false())
    return query.where(Customers.branch_id == user.branch_id)


def get_for_user(db: Session, user: Users, customer_id: uuid.UUID) -> Customers | None:
    query = scoped(select(Customers).where(Customers.customer_id == customer_id), user)
    return db.scalar(query)

def _filtered(
    user: Users,
    q: str | None = None,
    status: str | None = None,
    branch_id: uuid.UUID | None = None,
):
    query = scoped(select(Customers), user)
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

def get_all(
    db: Session,
    user: Users,
    q: str | None = None,
    status: str | None = None,
    branch_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Customers]:
    query = _filtered(user, q, status, branch_id)
    query = query.order_by(Customers.name_search).offset(skip).limit(min(max(limit, 1), 200))
    return list(db.scalars(query))

def count_all(
    db: Session,
    user: Users,
    q: str | None = None,
    status: str | None = None,
    branch_id: uuid.UUID | None = None,
) -> int:
    subquery = _filtered(user, q, status, branch_id).subquery()
    return db.scalar(select(func.count()).select_from(subquery)) or 0

def find_duplicate(
    db: Session,
    branch_id: uuid.UUID,
    name: str,
    phone: str | None,
    exclude_id: uuid.UUID | None = None,
) -> Customers | None:
    query = select(Customers).where(
        Customers.branch_id == branch_id,
        Customers.name_search == normalize_name(name),
    )
    if exclude_id:
        query = query.where(Customers.customer_id != exclude_id)
    phone_norm = normalize_phone(phone) or None
    for customer in db.scalars(query):
        if phones_match(customer.phone_norm, phone_norm):
            return customer
    return None

def _resolve_branch(db: Session, user: Users, branch_id: uuid.UUID | None) -> Branches:
    if user.user_role == UserRole.operasional_manager:
        if branch_id is None:
            raise ValueError("branch_id wajib diisi oleh Operasional Manager")
        branch = db.get(Branches, branch_id)
        if branch is None:
            raise ValueError("Branch tidak ditemukan")
        if user.company_id is not None and branch.company_id != user.company_id:
            raise PermissionError("Branch tersebut bukan milik company Anda")
        return branch

    if user.branch_id is None:
        raise ValueError("Branch Anda belum diatur, hubungi admin")
    if branch_id is not None and branch_id != user.branch_id:
        raise PermissionError("Anda hanya boleh memakai branch Anda sendiri")
    return db.get(Branches, user.branch_id)

def create_customer(db: Session, user: Users, data: CustomerCreate) -> Customers:
    branch = _resolve_branch(db, user, data.branch_id)
    duplicate = find_duplicate(db, branch.branch_id, data.name, data.phone)
    if duplicate:
        raise DuplicateCustomerError(duplicate)

    customer = Customers(
        name=data.name,
        phone=data.phone,
        email=data.email,
        category_id=data.category_id,
        branch_id=branch.branch_id,
        created_by=user.user_id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def ensure_customer(
    db: Session,
    user: Users,
    name: str,
    phone: str | None,
    category_id: uuid.UUID | None,
    branch_id: uuid.UUID | None,
) -> Customers:
    name = (name or "").strip()
    phone = (phone or "").strip() or None
    if not name:
        raise ValueError("Nama customer wajib diisi")

    branch = _resolve_branch(db, user, branch_id)
    existing = find_duplicate(db, branch.branch_id, name, phone)
    if existing:
        return existing

    customer = Customers(
        name=name,
        phone=phone,
        category_id=category_id,
        branch_id=branch.branch_id,
        created_by=user.user_id,
    )
    db.add(customer)
    db.flush()
    return customer

def update_customer(db: Session, user: Users, customer: Customers, data: CustomerUpdate) -> Customers:
    if customer.asis_partner_id:
        raise CustomerPostedError("Customer yang sudah diposting ke ASIS tidak dapat diubah")

    values = data.model_dump(exclude_unset=True)
    if values.get("name") is None:
        values.pop("name", None)
    if "branch_id" in values:
        branch_id = values.pop("branch_id")
        if branch_id is not None and branch_id != customer.branch_id:
            customer.branch_id = _resolve_branch(db, user, branch_id).branch_id

    new_name = values.get("name", customer.name)
    new_phone = values["phone"] if "phone" in values else customer.phone
    duplicate = find_duplicate(db, customer.branch_id, new_name, new_phone, exclude_id=customer.customer_id)
    if duplicate:
        raise DuplicateCustomerError(duplicate)

    for key, value in values.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer

def delete_customer(db: Session, customer: Customers) -> None:
    if customer.asis_partner_id:
        raise CustomerPostedError("Customer yang sudah diposting ke ASIS tidak dapat dihapus")
    db.delete(customer)
    db.commit()

def create_from_visit(db: Session, visit: CustomerVisits) -> Customers:
    branch = visit.user.branch if visit.user else None
    if branch is None:
        raise ValueError("User pembuat visit belum punya branch")

    existing = find_duplicate(db, branch.branch_id, visit.customer_name, visit.phone)
    if existing:
        return existing

    customer = Customers(
        name=visit.customer_name,
        phone=visit.phone,
        category_id=visit.category_id,
        branch_id=branch.branch_id,
        created_by=visit.user_id,
    )
    db.add(customer)
    db.flush()
    return customer
