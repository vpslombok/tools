# 🎵 YouTube Music Downloader

Aplikasi web yang dibuat dengan Flask dan JQuery untuk mengunduh audio dari YouTube dalam berbagai format berkualitas tinggi. Antarmuka yang modern dan responsif memudahkan untuk mengunduh satu lagu atau beberapa lagu secara massal.

![Screenshot Aplikasi](https://via.placeholder.com/800x450.png?text=App+Screenshot+Here)
*(Ganti placeholder di atas dengan screenshot aplikasi Anda)*

## ✨ Fitur Utama

- **Unduhan Tunggal**: Tempel URL YouTube untuk mengambil info video dan mengunduh audio.
- **Berbagai Pilihan Kualitas**: Pilih dari berbagai format dan bitrate, termasuk MP3 (320kbps, 256kbps), FLAC (lossless), M4A, dan lainnya.
- **Unduhan Massal (Batch)**: Unggah file `.txt` yang berisi daftar URL YouTube untuk mengunduh semuanya sekaligus.
- **Antarmuka Modern**: UI yang bersih, gelap, dan responsif dibangun dengan Bootstrap 5.
- **Proses Real-time**: Pantau status unduhan dengan progress bar dan pesan status.
- **Riwayat Unduhan**: Lihat daftar semua unduhan yang telah selesai.
- **Dukungan Multi-bahasa**: Antarmuka tersedia dalam Bahasa Inggris dan Bahasa Indonesia.
- **Status Sistem**: Panel dasbor menampilkan informasi penting seperti ketersediaan FFmpeg dan ruang disk.

## 🛠️ Tumpukan Teknologi (Tech Stack)

- **Backend**:
  - **Python 3**: Bahasa pemrograman utama.
  - **Flask**: Kerangka kerja web untuk menangani permintaan API.
  - **yt-dlp**: Pustaka inti untuk mengambil informasi dan mengunduh dari YouTube.
  - **SQLAlchemy**: ORM untuk berinteraksi dengan database (untuk riwayat).
  - **Gunicorn**: Server WSGI untuk production.

- **Frontend**:
  - **HTML5 / CSS3**: Struktur dan gaya halaman.
  - **JavaScript (ES6)**: Logika sisi klien.
  - **jQuery**: Manipulasi DOM dan permintaan AJAX.
  - **Bootstrap 5**: Kerangka kerja UI untuk desain yang responsif.
  - **Font Awesome**: Ikon.

## 📋 Prasyarat

Sebelum memulai, pastikan sistem Anda telah terinstal:

- **Python 3.8+**
- **pip** (Manajer paket Python)
- **FFmpeg**: Sangat penting untuk mengonversi audio ke format seperti MP3 dan FLAC.
  - **Windows**: Unduh dari situs resmi FFmpeg dan tambahkan ke PATH environment variable Anda.
  - **macOS (via Homebrew)**: `brew install ffmpeg`
  - **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install ffmpeg`

## 🚀 Memulai

Ikuti langkah-langkah ini untuk menjalankan proyek secara lokal.

### 1. Kloning Repositori

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. Buat dan Aktifkan Lingkungan Virtual (Virtual Environment)

Sangat disarankan untuk menggunakan lingkungan virtual untuk mengisolasi dependensi proyek.

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instal Dependensi

Instal semua pustaka Python yang diperlukan dari file `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Lingkungan

Aplikasi ini menggunakan file `.env` untuk mengelola konfigurasi. Buat file bernama `.env` di direktori root proyek dan tambahkan variabel yang diperlukan.

```env
# Contoh isi file .env
FLASK_ENV=development
DATABASE_URL=sqlite:///downloads.db
```

### 5. Jalankan Aplikasi

Gunakan server pengembangan Flask untuk menjalankan aplikasi secara lokal.

```bash
flask run
```

Aplikasi sekarang akan dapat diakses di `http://127.0.0.1:5000`.

## ⚖️ Penafian (Disclaimer)

Alat ini ditujukan untuk penggunaan pribadi dan hanya untuk mengunduh konten yang Anda miliki hak hukumnya atau konten yang tersedia di bawah lisensi domain publik atau lisensi serupa. Pengguna bertanggung jawab penuh untuk mematuhi persyaratan layanan YouTube dan undang-undang hak cipta yang berlaku. Pengembang tidak bertanggung jawab atas penyalahgunaan alat ini.

---

Dibuat dengan ❤️ untuk para pecinta musik.