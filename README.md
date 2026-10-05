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
```

| Variable | Wajib | Keterangan |
|---|---|---|
| `DATABASE_URL` | Ya | URL koneksi PostgreSQL dengan format `postgresql+psycopg://<user>:<password>@<host>:<port>/<nama_database>`. Basis data harus sudah dibuat sebelum migrasi dijalankan. |
| `SECRET_KEY` | Ya | Kunci rahasia untuk menandatangani token JWT. Gunakan rangkaian karakter acak yang panjang dan jangan dibagikan kepada pihak lain. Apabila nilainya diubah, seluruh token yang telah diterbitkan menjadi tidak berlaku. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Tidak | Masa berlaku token akses dalam satuan menit. Nilai bawaan adalah `60`. |
| `ASIS_BASE_URL` | Untuk fitur ASIS | URL dasar API ASIS yang digunakan untuk sinkronisasi *company* dan *branch*. Apabila kosong, *endpoint* `/asis` akan mengembalikan galat. |
| `ASIS_USERNAME` | Untuk fitur ASIS | Nama pengguna untuk masuk ke API ASIS. |
| `ASIS_PASSWORD` | Untuk fitur ASIS | Kata sandi untuk masuk ke API ASIS. |

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
