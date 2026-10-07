# CORA Backend

## 1. Penjelasan Project

**CORA (Customer Observation & Recording Application)** adalah aplikasi yang digunakan untuk mencatat aktivitas kunjungan pelanggan (*customer visit*) oleh tim sales di Amazink People Group. Repositori ini berisi sisi backend dari aplikasi tersebut.

Fitur utama:

- **Autentikasi** menggunakan JWT dengan tiga peran (*role*), yaitu `sales`, `branch_manager`, dan `operasional_manager`.
- **Customer visit**: sales mencatat kunjungan pelanggan (nama, nomor telepon, *source*, *category*, dan catatan). Data yang dapat dilihat dibatasi berdasarkan peran:
  - Sales hanya dapat melihat kunjungan miliknya sendiri.
  - Branch Manager dapat melihat kunjungan sales pada cabangnya.
  - Operasional Manager dapat melihat kunjungan sales pada perusahaannya.
- **Master data**: *category*, *source*, *company*, dan *branch*. Seluruh pengguna yang telah masuk (*login*) dapat membaca data ini, tetapi hanya Operasional Manager yang dapat mengubahnya.
- **Master Customer**: daftar customer per cabang yang ditarik dari ASIS (status *sudah diposting*) dan customer yang didaftarkan dari CORA (status *belum diposting*). Customer visit dipilih dari Master Customer, dan posting ke ASIS dilakukan dari customer, dengan pengecekan apakah customer tersebut sudah ada di ASIS.
- **Manajemen pengguna** dan **foto profil** yang disimpan langsung di dalam basis data.
- **Sinkronisasi ASIS**: mengambil data *company* dan *branch* dari sistem ASIS.

Dokumentasi seluruh *endpoint* tersedia pada Swagger (`/docs`) saat server berjalan.

## 2. Tech Stack

| Part | Tech |
|---|---|
| Bahasa pemrograman | Python 3.10+ |
| Framework | FastAPI, dijalankan menggunakan Uvicorn |
| Basis data | PostgreSQL |
| ORM dan migrasi | SQLAlchemy 2, Alembic |
| Driver basis data | psycopg 3 |
| Validasi data | Pydantic |
| Autentikasi | PyJWT (JWT), bcrypt (enkripsi kata sandi) |
| HTTP client | httpx (untuk memanggil API ASIS) |
| Unggah berkas | python-multipart |
| Konfigurasi | python-dotenv |

## 3. Environment Variable

Salin berkas `.env.example` menjadi `.env`, kemudian isi nilainya. Berkas `.env` telah diabaikan oleh git dan tidak boleh di-*commit*.

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
ASIS_BASE_URL=http://host:port/asis
ASIS_USERNAME=
ASIS_PASSWORD=
PUBLIC_API_KEY=
```

| Variable | Wajib | Keterangan |
|---|---|---|
| `DATABASE_URL` | Ya | URL koneksi PostgreSQL dengan format `postgresql+psycopg://<user>:<password>@<host>:<port>/<nama_database>`. Basis data harus sudah dibuat sebelum migrasi dijalankan. |
| `SECRET_KEY` | Ya | Kunci rahasia untuk menandatangani token JWT. Gunakan rangkaian karakter acak yang panjang dan jangan dibagikan kepada pihak lain. Apabila nilainya diubah, seluruh token yang telah diterbitkan menjadi tidak berlaku. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Tidak | Masa berlaku token akses dalam satuan menit. Nilai bawaan adalah `60`. |
| `ASIS_BASE_URL` | Untuk fitur ASIS | URL dasar API ASIS yang digunakan untuk sinkronisasi *company* dan *branch*. Apabila kosong, *endpoint* `/asis` akan mengembalikan galat. |
| `ASIS_USERNAME` | Untuk fitur ASIS | Nama pengguna untuk masuk ke API ASIS. |
| `ASIS_PASSWORD` | Untuk fitur ASIS | Kata sandi untuk masuk ke API ASIS. |
| `PUBLIC_API_KEY` | Untuk endpoint publik | Kunci untuk header `X-Api-Key` pada *endpoint* `/public`. Beberapa kunci dapat diisi dengan pemisah koma agar kunci dapat diganti tanpa menghentikan layanan. Apabila kosong, seluruh permintaan ke `/public` ditolak. |

Perintah untuk membuat `SECRET_KEY` secara acak:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 4. Menjalankan Project

Pastikan seluruh langkah pada bagian **Installation** telah dilakukan. Setelah itu, aktifkan *virtual environment* dan jalankan perintah berikut:

```bash
uvicorn app.main:app --reload
```

Server dapat diakses melalui alamat berikut:

- API: `http://127.0.0.1:8000`
- Swagger (dokumentasi interaktif): `http://127.0.0.1:8000/docs`
- Pemeriksaan koneksi basis data: `http://127.0.0.1:8000/health`

Konfigurasi CORS hanya mengizinkan *frontend* dari `http://localhost:5173` dan `http://127.0.0.1:5173`. Apabila *frontend* dijalankan pada alamat lain, tambahkan alamat tersebut pada berkas `app/middleware/CORS_middleware.py`.

Akun yang dapat digunakan untuk masuk setelah seeder dijalankan:

| Username | Password | Role |
|---|---|---|
| `operasional` | `123456` | Operasional Manager |
| `branch` | `123456` | Branch Manager |
| `sales` | `123456` | Sales |

Endpoint publik untuk kebutuhan *dashboard* eksternal tidak memakai token JWT, melainkan header `X-Api-Key`. Saat ini tersedia `GET /public/customer-visits/count` yang mengembalikan `{"count": <jumlah>}`. Seluruh parameter bersifat opsional dan digabung dengan logika AND: `date_from`, `date_to` (inklusif, berdasarkan waktu visit), `company_id`, `asis_company_id`, `branch_id`, dan `asis_branch_id`. Cabang sebuah visit ditentukan dari cabang customer-nya (cadangan: cabang user pembuat visit). ID yang tidak ditemukan menghasilkan 404, dan kunci yang salah menghasilkan 401.

```bash
curl -H "X-Api-Key: <kunci>" "http://127.0.0.1:8000/public/customer-visits/count?date_from=2026-10-01&date_to=2026-10-31&asis_branch_id=<id>"
```

Laporan aktivitas visit tersedia di `/reports` (memerlukan token JWT) dan seluruhnya mengikuti cakupan data tiap *role*: Operasional Manager melihat visit miliknya serta Sales dan Branch Manager di *company*-nya, Branch Manager melihat miliknya serta Sales di cabangnya, dan Sales hanya melihat visit miliknya. Seluruh parameter bersifat opsional: `date_from`, `date_to` (inklusif, berdasarkan waktu visit), dan `branch_id`.

| Endpoint | Isi |
|---|---|
| `GET /reports/summary` | Total visit, total customer unik, jumlah user aktif, serta jumlah visit yang sudah dan belum diposting ke ASIS |
| `GET /reports/visit-trend` | Jumlah visit dan customer unik per periode. Parameter tambahan `interval`: `day` (bawaan), `week`, atau `month`. Periode tanpa visit tetap ditampilkan dengan nilai 0 |
| `GET /reports/category` | Jumlah visit per kategori beserta persentasenya |
| `GET /reports/source` | Jumlah visit per sumber beserta persentasenya |
| `GET /reports/sales-performance` | Jumlah visit, customer unik, visit terposting, dan visit terakhir per user, diurutkan dari visit terbanyak. Sales aktif tanpa visit tetap ditampilkan |

## 5. Installation

Prasyarat: **Python 3.10+** dan **PostgreSQL** yang sudah berjalan.

1. Lakukan *clone* repositori, kemudian masuk ke direktorinya.

   ```bash
   git clone <url-repo>
   cd BE_CORA
   ```

2. Buat dan aktifkan *virtual environment*.

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # Linux / macOS
   ```

3. Pasang seluruh dependensi.

   ```bash
   pip install -r requirements.txt
   ```

4. Buat basis data kosong di PostgreSQL, kemudian siapkan berkas `.env` (lihat bagian **Environment Variable**).

   ```bash
   cp .env.example .env
   ```

5. Jalankan migrasi untuk membuat tabel.

   ```bash
   alembic upgrade head
   ```

6. Isi data awal (*source* dan tiga akun contoh). Data *category*, *company*, dan *branch* diambil dari ASIS melalui fitur Sync ASIS oleh Operasional Manager.

   ```bash
   python -m app.seeders.seed
   ```

7. Setelah *company*, *branch*, dan *category* tersinkron, Operasional Manager dapat menarik Master Customer dari ASIS dengan `POST /customers/sync` (opsional dengan body `{"branch_id": "<id branch>"}` untuk satu cabang). Proses berjalan di *background* karena jumlah customer di ASIS besar (puluhan ribu); pantau lewat `GET /customers/sync/status`.
