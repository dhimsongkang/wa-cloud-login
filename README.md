# WhatsApp Desktop Auto Login Tool

Tool otomatisasi untuk mengecek dan memproses login daftar nomor WhatsApp pada **WhatsApp Desktop (Windows)**.

## Fitur Utama
1. **Otomatisasi Input Nomor**: Membaca nomor dari file [nomor.txt](file:///c:/Users/dimas/.gemini/antigravity/scratch/whatsapp%20auto%20login/nomor.txt) satu per satu dan memasukkannya ke WhatsApp Desktop.
2. **Auto Skip jika Minta Kode di Handphone (Pairing Code)**: Jika nomor meminta kode tautan 8 digit di HP (*"Enter code on phone"* seperti screenshot Anda), tool akan **otomatis melewatinya (SKIP)** dan langsung lanjut ke nomor berikutnya.
3. **Berhenti jika Minta OTP SMS**: Jika nomor meminta kode SMS (OTP), tool akan **seketika menghentikan semua proses otomatis**, membunyikan peringatan, dan menunggu Anda memasukkan OTP secara manual. Setelah selesai, cukup ketik `next` di konsol untuk melanjutkan ke nomor berikutnya.
4. **Pencatatan Hasil Lengkap**: Status setiap nomor (SKIPPED / OTP_SMS / FAILED) dicatat secara rapi di file `result.txt` beserta waktu pemrosesan dan log rinci di `wa_login.log`.

---

## Persiapan & Instalasi

Semua dependensi sudah terpasang. Jika ingin memastikan kembali:
```bash
pip install -r requirements.txt
```

---

## Cara Penggunaan

1. **Siapkan Nomor**:
   Buka file [nomor.txt](file:///c:/Users/dimas/.gemini/antigravity/scratch/whatsapp%20auto%20login/nomor.txt) dan masukkan daftar nomor telepon Anda (satu nomor per baris), contoh:
   ```text
   +6281234567890
   +258833553805
   +6289876543210
   ```

2. **Jalankan Tool**:
   Buka terminal/PowerShell di folder ini, lalu jalankan:
   ```bash
   python wa_auto_login.py
   ```

3. **Alur Kerja**:
   - Tool akan otomatis mendeteksi atau membuka WhatsApp Desktop.
   - Tool menavigasi ke halaman input nomor telepon.
   - **Jika muncul "Enter code on phone"** -> Otomatis di-skip, lanjut nomor selanjutnya.
   - **Jika muncul permintaan OTP SMS** -> Muncul notifikasi suara & instruksi di konsol:
     ```text
     [!] PERHATIAN: NOMOR MEMINTA OTP SMS!
         Nomor Telepon: +6281234567890
         Semua proses otomatis dihentikan.
         Silakan masukkan kode OTP SMS secara manual di WhatsApp Desktop.

     Ketik 'next' untuk lanjut ke nomor berikutnya, atau 'quit' untuk berhenti: 
     ```
     Ketik `next` lalu tekan **Enter** setelah selesai.

4. **Cek Hasil**:
   Lihat ringkasan di layar atau buka file `result.txt` untuk melihat laporan lengkap per nomor.
