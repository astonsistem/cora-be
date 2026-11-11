# CORA Backend

**CORA (Customer Observation & Recording Application)** adalah aplikasi untuk mencatat kunjungan pelanggan (*customer visit*) oleh tim sales Amazink People Group. Repositori ini berisi backend-nya (FastAPI + PostgreSQL).

Dokumentasi seluruh endpoint ada di Swagger (`/docs`) saat server berjalan.

## Fitur

- **Autentikasi JWT** (access token dan refresh token) dengan empat role.
- **Customer visit**, **Master Customer**, **voucher**, **laporan** (`/reports`), manajemen user dan foto profil.
- **Master data**: category, source, company, branch.
- **Sync ASIS**: menarik company, branch, category, dan customer dari sistem ASIS.
- **Endpoint publik** (`/public`) memakai header `X-Api-Key`.

## Role dan Hak Akses

| Role | Cakupan data | Catatan |
|---|---|---|
| `sales` | Visit miliknya sendiri | |
| `branch_manager` | Visit sales di branch-nya | Mengelola voucher branch-nya |
| `operasional_manager` | Company miliknya | Sync ASIS hanya untuk company-nya. Tidak bisa mengubah company |
| `superadmin` | Semua company dan branch | Tidak terikat company/branch. Satu-satunya yang bisa membuat user, serta menambah/mengubah/menghapus company |

Superadmin memilih company dan branch sendiri saat membuat customer visit.

## Tech Stack

Python 3.10+, FastAPI (Uvicorn), PostgreSQL, SQLAlchemy 2 + Alembic, psycopg 3, Pydantic, PyJWT, bcrypt, httpx.

## Instalasi

Prasyarat: Python 3.10+ dan PostgreSQL yang sudah berjalan.

```bash
git clone <url-repo>
cd BE_CORA
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env          # lalu isi nilainya
alembic upgrade head
python -m app.seeders.seed    # data awal dan akun contoh
```

Seeder menghapus semua user yang ada. Jangan dijalankan di database yang sudah berisi data.

Setelah itu, Superadmin atau OM menjalankan Sync ASIS untuk mengisi company, branch, dan category. Master Customer ditarik lewat `POST /customers/sync` (berjalan di background, status di `GET /customers/sync/status`).

## Menjalankan

```bash
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Cek database: `http://127.0.0.1:8000/health`

CORS hanya mengizinkan `http://localhost:5173` dan `http://127.0.0.1:5173`. Untuk alamat FE lain, ubah `app/middleware/CORS_middleware.py`.

Akun contoh setelah seeder (password `123456`): `superadmin`, `operasional`, `branch`, `sales`.

## Environment Variable

| Variable | Wajib | Keterangan |
|---|---|---|
| `DATABASE_URL` | Ya | `postgresql+psycopg://user:password@host:5432/dbname` |
| `SECRET_KEY` | Ya | Kunci penanda JWT. Jika diganti, semua token tidak berlaku |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Tidak | Bawaan `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Tidak | Bawaan `1` |
| `ASIS_BASE_URL`, `ASIS_USERNAME`, `ASIS_PASSWORD` | Untuk fitur ASIS | Akses ke API ASIS |
| `PUBLIC_API_KEY` | Untuk `/public` | Header `X-Api-Key`. Boleh beberapa kunci dipisah koma |
| `CUSTOMER_TRASH_RETENTION_DAYS` | Tidak | Lama customer terhapus disimpan sebelum dihapus permanen. Bawaan `90` |
| `LOG_LEVEL` | Tidak | `DEBUG`, `INFO` (bawaan), `WARNING`, `ERROR` |

Membuat `SECRET_KEY` acak:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Konvensi API

Semua respons memakai satu bentuk, sukses maupun galat:

```json
{ "success": true, "message": "Data retrieved successfully", "data": [] }
```

- Total data pada daftar ada di header `X-Total-Count`.
- Penghapusan mengembalikan 200 dengan `data: null`.
- Router baru harus memakai `ApiRouter` (`app/core/response/envelope.py`), bukan `APIRouter`.
- `POST /auth/login` mengembalikan `access_token` (header `Authorization: Bearer <token>`) dan `refresh_token` (hanya untuk `POST /auth/refresh`).

Endpoint publik, contoh:

```bash
curl -H "X-Api-Key: <kunci>" "http://127.0.0.1:8000/public/customer-visits/count?date_from=2026-10-01&date_to=2026-10-31"
```

## Catatan Perilaku

- **Customer terhapus** memakai *soft delete* (hanya OM/Superadmin) dan dihapus permanen otomatis setelah masa simpan.
- **Sync customer**: customer yang sudah diposting tetapi hilang di ASIS dikembalikan menjadi `pending`. Hal ini dilewati dengan peringatan jika ASIS mengembalikan 0 customer atau lebih dari 50% customer branch hilang.
- **Sync ASIS** dibatasi per company untuk OM. Superadmin menyinkronkan semuanya.
