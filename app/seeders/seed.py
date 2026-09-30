
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Category, Sources, Users
from app.models.users import UserRole
from app.security import hash_password

db = SessionLocal()

db.query(Users).delete()

CATEGORIES = [
    {"name": "Retail", "description": "Pelanggan perorangan"},
    {"name": "Distributor"},
    {"name": "Corporate"},
]

SOURCES = [
    {"name": "Website"},
    {"name": "Referensi"},
    {"name": "Event"},
    {"name": "Cold Call"},
]

USERS = [
    {"username": "operasional", "first_name": "Admin", "last_name": "Operasional", "user_role": UserRole.operasional_manager, "password": "123456"},
    {"username": "branch", "first_name": "Branch", "last_name": "Manager", "user_role": UserRole.branch_manager, "password": "123456"},
    {"username": "sales", "first_name": "Sales", "last_name": "Satu", "user_role": UserRole.sales, "password": "123456"},
]


def get_or_create(db: Session, model, lookup: dict, defaults: dict | None = None):
    obj = db.scalar(select(model).filter_by(**lookup))
    if obj:
        return obj, False
    obj = model(**lookup, **(defaults or {}))
    db.add(obj)
    db.flush()
    return obj, True


def seed_simple(db: Session, model, rows: list[dict]) -> int:
    created = 0
    for row in rows:
        row = dict(row)
        _, is_new = get_or_create(db, model, {"name": row.pop("name")}, row)
        created += is_new
    return created

def seed_users(db: Session) -> int:
    created = 0
    for row in USERS:
        row = dict(row)
        _, is_new = get_or_create(
            db,
            Users,
            {"username": row.pop("username")},
            {**row, "password": hash_password(row["password"])},
        )
        created += is_new
    return created


def main() -> None:
    with SessionLocal() as db:
        n_cat = seed_simple(db, Category, CATEGORIES)
        n_src = seed_simple(db, Sources, SOURCES)
        n_users = seed_users(db)
        db.commit()

    print(f"Category baru: {n_cat}, Sources baru: {n_src}, Users baru: {n_users}")


if __name__ == "__main__":
    main()
