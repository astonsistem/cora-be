import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.users import UserRole, Users
from app.security import token_service

S, B, O = "sales", "branch_manager", "operasional_manager"
ALL = {S, B, O}
MANAGER = {B, O}
OM = {O}
SHORT = {S: "Sales", B: "BM", O: "OM"}


EXPECTED = [
    # Auth: semua role boleh mengakses profil sendiri
    ("GET", "/auth/me", ALL),

    # Master data: OM only
    ("GET", "/users/", OM),
    ("GET", "/users/{id}", OM),
    ("POST", "/users/", OM),
    ("PATCH", "/users/{id}", OM),
    ("DELETE", "/users/{id}", OM),

    ("GET", "/companies/", OM),
    ("POST", "/companies/", OM),
    ("PATCH", "/companies/{id}", OM),
    ("DELETE", "/companies/{id}", OM),

    ("GET", "/branches/", OM),
    ("POST", "/branches/", OM),
    ("PATCH", "/branches/{id}", OM),
    ("DELETE", "/branches/{id}", OM),

    ("GET", "/categories/", OM),
    ("POST", "/categories/", OM),
    ("PATCH", "/categories/{id}", OM),
    ("DELETE", "/categories/{id}", OM),

    ("GET", "/sources/", OM),
    ("POST", "/sources/", OM),
    ("PATCH", "/sources/{id}", OM),
    ("DELETE", "/sources/{id}", OM),

    # ASIS: preview dan sync hanya OM
    ("GET", "/asis/preview", OM),

    # Customer
    # Semua role boleh melihat customer sesuai cakupan datanya
    ("GET", "/customers/", ALL),
    ("GET", "/customers/sync/status", OM),
    ("GET", "/customers/deleted", OM),
    ("GET", "/customers/{id}", ALL),

    # Semua role boleh membuat dan mengedit customer
    ("POST", "/customers/", ALL),
    ("PATCH", "/customers/{id}", ALL),

    # Hapus dan restore hanya OM
    ("DELETE", "/customers/{id}", OM),
    ("POST", "/customers/{id}/restore", OM),

    # Post customer ke ASIS: OM dan BM
    ("POST", "/customers/{id}/post-to-asis", MANAGER),

    # Customer visit: semua role boleh membaca
    ("GET", "/customer-visits/", ALL),
    ("GET", "/customer-visits/summary", ALL),
    ("GET", "/customer-visits/{id}", ALL),

    # Semua role boleh membuat customer visit
    ("POST", "/customer-visits/", ALL),

    # Asumsi sementara: edit dan hapus visit juga boleh
    # untuk semua role. Sesuaikan jika aturan bisnisnya berbeda.
    ("PATCH", "/customer-visits/{id}", ALL),
    ("DELETE", "/customer-visits/{id}", ALL),

    # Reports: hanya OM dan BM
    ("GET", "/reports/summary", MANAGER),
    ("GET", "/reports/visit-trend", MANAGER),
    ("GET", "/reports/category", MANAGER),
    ("GET", "/reports/source", MANAGER),
    ("GET", "/reports/sales-performance", MANAGER),
    ("GET", "/reports/sales-performance/{id}", MANAGER),
]


SKIPPED = ["POST /asis/sync", "POST /asis/apply", "POST /customers/sync", "foto user (PUT/DELETE /users/{id}/photo)"]

EMPTY_BODY = {"POST": {}, "PATCH": {}}
LISTS = [
    "/customers/",
    "/customer-visits/",
    "/reports/summary",
    "/reports/sales-performance",
]


def login_users():
    picked = {}
    with SessionLocal() as db:
        for user in db.query(Users).filter(Users.is_active.is_(True)).order_by(Users.username):
            picked.setdefault(user.user_role.value, (user.username, user.user_id))
    return picked


def call(client, token, method, path):
    url = path.replace("{id}", str(uuid.uuid4()))
    return client.request(method, url, json=EMPTY_BODY.get(method), headers={"Authorization": f"Bearer {token}"}).status_code


def main():
    users = login_users()
    roles = [role for role in (S, B, O) if role in users]
    tokens = {role: token_service.create_access_token(users[role][1]) for role in roles}
    client = TestClient(app)

    print("Akun yang dipakai:", ", ".join(f"{SHORT[r]}={users[r][0]}" for r in roles))
    print("Aturan: 403 = ditolak. Selain 401/403 (200, 404, 422, dst.) = lolos pengecekan role.\n")
    print(f"{'ENDPOINT':<46}" + "".join(f"{SHORT[r]:<14}" for r in roles))

    mismatches = []
    for method, path, allowed in EXPECTED:
        cells = []
        for role in roles:
            code = call(client, tokens[role], method, path)
            permitted = code not in (401, 403)
            should = role in allowed
            cells.append(f"{code:<4}{'ok' if permitted == should else 'BEDA':<10}")
            if permitted != should:
                mismatches.append((method, path, SHORT[role], code, "boleh" if should else "ditolak"))
        print(f"{method + ' ' + path:<46}" + "".join(cells))

    print("\nJumlah data yang terlihat per role (cakupan data):")
    print(f"{'ENDPOINT':<46}" + "".join(f"{SHORT[r]:<14}" for r in roles))
    for path in LISTS:
        cells = []
        for role in roles:
            response = client.get(path, headers={"Authorization": f"Bearer {tokens[role]}"})
            body = response.json()
            total = response.headers.get("x-total-count")
            size = len(body) if isinstance(body, list) else body.get("total_visits", "-")
            cells.append(f"{(total or size)!s:<14}")
        print(f"{'GET ' + path:<46}" + "".join(cells))
    pending = {}
    for role in roles:
        response = client.get("/customers/?status=pending", headers={"Authorization": f"Bearer {tokens[role]}"})
        pending[role] = response.headers.get("x-total-count")
    print(f"{'GET /customers/?status=pending':<46}" + "".join(f"{pending[r]!s:<14}" for r in roles))

    print("\nTidak dicek (mengubah data atau butuh ASIS):", "; ".join(SKIPPED))
    if mismatches:
        print(f"\nBEDA dari yang diharapkan ({len(mismatches)}):")
        for method, path, role, code, expected in mismatches:
            print(f"  {method} {path}: {role} dapat {code}, seharusnya {expected}")
        sys.exit(1)
    print("\nSemua sesuai tabel EXPECTED di bagian atas skrip.")


if __name__ == "__main__":
    main()
