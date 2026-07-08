# cypy

<p align="center">
  <img src="assets/favicon.png" width="128" alt="cypy Logo" />
</p>

<p align="center">
  <a href="#english">English</a> | <a href="#bahasa-indonesia">Bahasa Indonesia</a>
</p>

---

<h2 id="english">English Version</h2>

**cypy** is a modern manga translator application utilizing YOLOv8 to accurately detect speech bubbles and Google Gemini API / OpenAI API to translate comic panels while keeping original artwork clean and typography well-fitted.

The application offers two operation modes:
- **GUI Mode:** A sleek, pitch-black retro graphical interface inspired by the **xidown** aesthetic, featuring Consolas monospace font, pixel-perfect 1px borders, and full **Drag & Drop** support.
- **CLI Mode:** An interactive command-line interface for fast and efficient translation directly from your terminal.

### Features

- **Xidown-inspired Retro GUI:** Deep black background (`#000000`), dark gray panel cards (`#121212`), Consolas monospace typography, and sharp, pixel-perfect 1px borders.
- **Drag & Drop Support (GUI):** Drag any manga files (Images, PDF, ZIP, CBZ, RAR, CBR) or directories and drop them directly onto the GUI window to automatically populate the source path.
- **Interactive Terminal Loop (CLI):** Switch target languages, LLM models, and AI providers on the fly, or tweak bubble layout padding and font scales dynamically.
- **Smart Hybrid Storage:**
  - **Portable Mode:** Saves your configuration to `./data/settings.json` when run from local writable folders.
  - **Installed Mode:** Automatically redirects settings to `%LOCALAPPDATA%/cypy/settings.json` if run from protected system folders (like `Program Files`) to prevent permission errors and preserve preferences during upgrades.
- **Multi-Language Translation:** Translate manga to English, Indonesian, Japanese, Mandarin, Spanish, Portuguese, Javanese, Korean, Russian, and Thai.
- **Multi-Provider AI Engines:** Out-of-the-box support for **Google Gemini**, **OpenAI**, **Zen** (free, no API key required), **OpenCode Go**, **OpenRouter**, and **Custom Provider** (OpenAI-compatible base URL & custom model).
- **Official Publisher Metadata:** Built Windows executables (`.exe`) are dynamically stamped with publisher properties (**indravoyager**).

### Installation & Setup

#### Prerequisites
- **Python:** Version `3.8` to `3.11` (Python `3.10` recommended).

#### Step 1: Clone the Repository & Prepare Virtual Environment
```bash
# 1. Clone cypy repository
git clone https://github.com/indravoyager/cypy.git
cd cypy

# 2. Create virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate
```

#### Step 2: Install Dependencies & Application
```bash
pip install -e .
```

#### Step 3: Run the Application
Once installed, you can use the registered shortcut command `cypy` directly from your terminal:
- **GUI Mode (Recommended):**
  ```bash
  cypy --gui
  ```
- **CLI Mode (Interactive Terminal):**
  ```bash
  cypy
  ```

### Interactive CLI Commands

When running in **CLI Mode**, you can type these commands directly in the prompt before dropping your files:

| Command | Description |
| :--- | :--- |
| `lang` / `switch` | Dynamically select/change the target translation language. |
| `provider` / `api` | Choose/switch the active LLM provider (Gemini, OpenAI, Zen, etc.). |
| `model` | Instantly change the active LLM model name. |
| `status` | Display current API key status and configurations. |
| `tweak` | Open the layout tweak menu to adjust padding margins, font scales, etc. |
| `help` | Print list of available commands. |
| `stop` / `exit` | Exit the application. |

### Compiling Standalone Executable (.exe)
To package `cypy` into a standalone Windows executable (`.exe`) stamped with the **indravoyager** metadata, run:
```bash
python build.py
```

---

<h2 id="bahasa-indonesia">Versi Bahasa Indonesia</h2>

**cypy** adalah alat bantu penerjemah manga modern menggunakan model YOLOv8 untuk mendeteksi balon teks secara presisi dan Google Gemini API / OpenAI API untuk menerjemahkan teks komik dengan menjaga keaslian artwork halaman manga.

Aplikasi ini hadir dengan dua pilihan mode operasi:
- **GUI Mode:** Antarmuka visual retro bertema hitam pekat (*pitch black*) dengan aksen pink khas **xidown**, menggunakan font monospace **Consolas**, dan mendukung fitur seret-taruh berkas (**Drag & Drop**).
- **CLI Mode:** Antarmuka baris perintah (Command Line Interface) interaktif untuk penerjemahan cepat langsung dari terminal.

### Fitur Utama

- **Aestetika Retro Xidown (GUI):** Antarmuka grafis berwarna hitam pekat (`#000000`), kartu panel abu-abu gelap (`#121212`), font monospace **Consolas**, dan outline border *pixel-perfect* 1px.
- **Drag & Drop Berkas (GUI):** Seret dan letakkan berkas manga (Gambar/PDF/ZIP/CBZ/RAR/CBR) atau folder apa saja langsung ke jendela GUI untuk mengisi jalur file secara otomatis!
- **Perintah Interaktif Terminal (CLI):** Ubah bahasa target, penyedia AI, model LLM, atau sesuaikan margin pembersihan teks secara instan saat program sedang berjalan di terminal.
- **Penyimpanan Hibrida Pintar (Hybrid Storage):** 
  - **Mode Portable:** Menyimpan pengaturan di `./data/settings.json` jika dijalankan secara portable.
  - **Mode Terinstal:** Otomatis menyimpan pengaturan di `%LOCALAPPDATA%/cypy/settings.json` jika dipasang di direktori sistem (seperti `Program Files`) untuk menghindari eror izin akses (*PermissionError*).
- **Dukungan Multi-Bahasa:** Menerjemahkan manga ke berbagai bahasa target (English, Indonesian, Japanese, Mandarin, Spanish, Portuguese, Javanese, Korean, Russian, dan Thai).
- **Multi-Provider AI:** Dukungan instan ke **Google Gemini**, **OpenAI**, **Zen** (gratis, tanpa API key), **OpenCode Go**, **OpenRouter**, dan **Custom Provider** (Base URL & Model kustom).
- **Metadata Resmi Windows:** File eksekusi hasil kompilasi Windows (`.exe`) otomatis menyematkan informasi metadata penerbit (**indravoyager**) secara terintegrasi.

### Panduan Instalasi & Cara Menjalankan

#### Persyaratan Sistem
- **Python:** Versi `3.8` hingga `3.11` (Disarankan Python `3.10`).

#### Langkah 1: Kloning & Persiapan Virtual Environment
```bash
# 1. Kloning repositori cypy
git clone https://github.com/indravoyager/cypy.git
cd cypy

# 2. Buat virtual environment
python -m venv venv

# 3. Aktifkan virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate
```

#### Langkah 2: Instalasi Dependensi & Aplikasi
```bash
pip install -e .
```

#### Langkah 3: Menjalankan Aplikasi
Setelah proses instalasi selesai, Anda dapat memanggil perintah pintas `cypy` langsung dari baris perintah terminal Anda:
- **GUI Mode (Rekomendasi):**
  ```bash
  cypy --gui
  ```
- **CLI Mode (Interactive Terminal):**
  ```bash
  cypy
  ```

### Panduan Perintah Interaktif (CLI Mode)

Saat aplikasi berjalan dalam **Mode CLI**, Anda dapat mengetikkan perintah berikut langsung di kolom input sebelum men-drag file manga:

| Perintah | Deskripsi |
| :--- | :--- |
| `lang` / `switch` | Mengubah bahasa target terjemahan secara dinamis. |
| `provider` / `api` | Mengubah penyedia kecerdasan buatan (Gemini, OpenAI, Zen, dll.). |
| `model` | Mengubah nama model LLM yang aktif secara instan. |
| `status` | Menampilkan ringkasan status konfigurasi dan API Key saat ini. |
| `tweak` | Masuk ke menu eksperimental untuk mengubah margin padding balon teks, ukuran font, dsb. |
| `help` | Menampilkan panduan bantuan daftar perintah. |
| `stop` / `exit` | Keluar dari aplikasi. |

### Mengompilasi Rilis Standalone (.exe)
Untuk mengompilasi kode program menjadi file eksekusi mandiri siap pakai (`.exe` di Windows) yang menyertakan metadata **indravoyager**, jalankan perintah:
```bash
python build.py
```

---

## License

[MIT](LICENSE)
