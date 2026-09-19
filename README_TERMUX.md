# Panduan Menjalankan di Cloudphone (Termux Root)

Tool ini dirancang khusus untuk berjalan di dalam **Termux pada Android Cloudphone yang sudah memiliki akses ROOT**.

---

## 1. Persiapan di Termux Cloudphone

Buka aplikasi **Termux** di cloudphone Anda, lalu jalankan perintah berikut:

```bash
# Update package Termux
pkg update -y && pkg install python tsu -y

# Minta izin penyimpanan
termux-setup-storage
```

---

## 2. Salin File Script & Daftar Nomor

Buat atau salin file [wa_termux_login.py](file:///c:/Users/dimas/.gemini/antigravity/scratch/whatsapp%20auto%20login/wa_termux_login.py) dan [nomor.txt](file:///c:/Users/dimas/.gemini/antigravity/scratch/whatsapp%20auto%20login/nomor.txt) ke folder Termux Anda.

Contoh membuat file `nomor.txt` di Termux:
```bash
nano nomor.txt
```
*(Paste daftar nomor WhatsApp Anda, lalu tekan Ctrl+O untuk simpan dan Ctrl+X untuk keluar)*

---

## 3. Jalankan Tool

Jalankan script dengan Python:
```bash
python wa_termux_login.py
```
*(Jika muncul pop-up izin Superuser / Root, pilih **Grant / Always Allow**)*

---

## 4. Cara Kerja Otomatis:
1. Script akan membuka WhatsApp secara otomatis.
2. Membaca nomor dari `nomor.txt` dan mengisikannya ke form pendaftaran.
3. **Jika nomor meminta kode verifikasi di HP lain / device lain / Banned**:
   - Script akan **otomatis melewatinya (SKIP)** dan melanjutkan ke nomor berikutnya.
4. **Jika nomor meminta OTP SMS**:
   - Proses **seketika berhenti**.
   - Muncul notifikasi peringatan di Termux:
     ```text
     [!] PERHATIAN: NOMOR MEMINTA KODE OTP SMS!
         Nomor: +25883xxxxxx
         Semua proses otomatis dihentikan sementara.
         Silakan masukkan OTP SMS langsung di WhatsApp.

     Ketik 'next' untuk lanjut ke nomor berikutnya, atau 'quit' untuk berhenti:
     ```
   - Masukkan kode OTP di WhatsApp, lalu ketik `next` di Termux untuk beralih ke nomor selanjutnya.
5. Seluruh riwayat dan status setiap nomor tersimpan rapi di file `result.txt`.
