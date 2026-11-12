from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database.database import SessionLocal
from app.core.security.security import PasswordHasher, password_hasher
from app.models import Sources, Users
from app.models.users import UserRole

SOURCES = [
    {"name": "Website"},
    {"name": "Referensi"},
    {"name": "Event"},
    {"name": "Cold Call"},
]

USERS = [
    {"username": "superadmin", "first_name": "Super", "last_name": "Admin", "user_role": UserRole.superadmin, "password": "123456"},
    {"username": "operasional", "first_name": "Admin", "last_name": "Operasional", "user_role": UserRole.operasional_manager, "password": "123456"},
    {"username": "branch", "first_name": "Branch", "last_name": "Manager", "user_role": UserRole.branch_manager, "password": "123456"},
    {"username": "sales", "first_name": "Sales", "last_name": "Satu", "user_role": UserRole.sales, "password": "123456"},
]


class Seeder:
    def __init__(self, db: Session, hasher: PasswordHasher = password_hasher):
        self.db = db
        self.hasher = hasher

    def run(self) -> dict[str, int]:
        result = {
            "sources": self.seed_sources(SOURCES),
            "users": self.seed_users(USERS),
        }
        self.db.commit()
        return result

    def seed_sources(self, rows: list[dict]) -> int:
        return sum(self._get_or_create(Sources, {"name": row["name"]}) for row in rows)

    def seed_users(self, rows: list[dict]) -> int:
        created = 0
        for row in rows:
            defaults = {
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "user_role": row["user_role"],
                "password": self.hasher.hash(row["password"]),
            }
            created += self._get_or_create(Users, {"username": row["username"]}, defaults)
        return created

    def _get_or_create(self, model, lookup: dict, defaults: dict | None = None) -> bool:
        if self.db.scalar(select(model).filter_by(**lookup)):
            return False
        self.db.add(model(**lookup, **(defaults or {})))
        self.db.flush()
        return True


def main() -> None:
    with SessionLocal() as db:
        result = Seeder(db).run()

    print(f"Sources baru: {result['sources']}, Users baru: {result['users']}")


if __name__ == "__main__":
    main()
