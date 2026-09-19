#!/usr/bin/env python3
"""
WhatsApp Cloudphone (Termux Root) Auto Login Tool
=================================================
Khusus untuk Android Cloudphone yang sudah ROOT via Termux.

Fitur:
- Membaca nomor dari nomor.txt
- Otomatis input nomor ke WhatsApp Mobile via su shell
- Membaca respon layar via uiautomator dump (sangat presisi tanpa OCR)
- Jika nomor meminta verifikasi di HP / bermasalah -> OTOMATIS SKIP & Reset WhatsApp
- Jika nomor meminta OTP SMS -> PROSES BERHENTI, menunggu input manual user
- Mencatat hasil ke result.txt
"""

import os
import sys
import time
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

# Konfigurasi Paket WhatsApp (Mendukung WhatsApp Business & WhatsApp Standar)
WA_BUSINESS_PACKAGE = "com.whatsapp.w4b"
WA_STANDARD_PACKAGE = "com.whatsapp"

WA_PACKAGE = WA_BUSINESS_PACKAGE
WA_MAIN_ACTIVITY = f"{WA_PACKAGE}/.Main"
DUMP_XML_PATH = "/sdcard/wa_dump.xml"

def run_root(cmd):
    """Menjalankan perintah shell dengan hak akses root (su)."""
    full_cmd = f"su -c '{cmd}'"
    result = subprocess.run(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {msg}"
    print(formatted)
    try:
        with open("wa_termux.log", "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def record_result(nomor, status, detail=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} | {nomor} | {status} | {detail}\n"
    try:
        with open("result.txt", "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

def check_root():
    """Memeriksa apakah Termux memiliki akses root."""
    res = run_root("id")
    if "uid=0(root)" in res:
        log("Akses ROOT terverifikasi!", "SUCCESS")
        return True
    else:
        log("Gagal mendapatkan akses ROOT. Pastikan izin Superuser sudah diizinkan di Termux.", "ERROR")
        return False

def dump_ui():
    """Mengambil snapshot tampilan XML layar saat ini."""
    run_root(f"uiautomator dump {DUMP_XML_PATH} && chmod 777 {DUMP_XML_PATH}")
    time.sleep(0.5)
    
    xml_content = ""
    # Coba baca dari /sdcard/wa_dump.xml
    if os.path.exists(DUMP_XML_PATH):
        try:
            with open(DUMP_XML_PATH, "r", encoding="utf-8", errors="ignore") as f:
                xml_content = f.read()
        except Exception:
            xml_content = run_root(f"cat {DUMP_XML_PATH}")
    else:
        xml_content = run_root(f"cat {DUMP_XML_PATH}")
        
    return xml_content

def parse_bounds(bounds_str):
    """Mengubah format bounds '[x1,y1][x2,y2]' menjadi titik tengah (center_x, center_y)."""
    match = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
    if len(match) == 2:
        x1, y1 = int(match[0][0]), int(match[0][1])
        x2, y2 = int(match[1][0]), int(match[1][1])
        return (x1 + x2) // 2, (y1 + y2) // 2
    return None

def find_element(xml_str, text_pattern=None, res_id=None):
    """Mencari elemen di XML berdasarkan teks atau resource-id."""
    if not xml_str:
        return None, None
    try:
        root = ET.fromstring(xml_str)
        for node in root.iter("node"):
            n_text = node.get("text", "")
            n_desc = node.get("content-desc", "")
            n_id = node.get("resource-id", "")
            bounds = node.get("bounds", "")

            # Cocokkan teks atau content-desc
            if text_pattern:
                pat = text_pattern.lower()
                if pat in n_text.lower() or pat in n_desc.lower():
                    return parse_bounds(bounds), n_text

            # Cocokkan resource-id
            if res_id and res_id in n_id:
                return parse_bounds(bounds), n_text
    except Exception as e:
        pass
    return None, None

def tap(x, y):
    """Menekan layar di koordinat (x, y)."""
    run_root(f"input tap {x} {y}")
    time.sleep(0.5)

def type_text(text):
    """Mengetik teks menggunakan input text."""
    run_root(f"input text '{text}'")
    time.sleep(0.5)

def press_key(key_code):
    """Menekan tombol keyboard tertentu (cth: 66 untuk ENTER, 4 untuk BACK)."""
    run_root(f"input keyevent {key_code}")
    time.sleep(0.5)

def open_whatsapp():
    """Membuka aplikasi WhatsApp."""
    run_root(f"am start -n {WA_MAIN_ACTIVITY}")
    time.sleep(2)

def reset_whatsapp():
    """Me-reset data WhatsApp agar kembali ke halaman awal pendaftaran."""
    log("Membersihkan data WhatsApp (Reset)...", "INFO")
    run_root(f"pm clear {WA_PACKAGE}")
    time.sleep(1.5)
    open_whatsapp()
    time.sleep(2)

def detect_whatsapp_package():
    """Mendeteksi apakah WhatsApp Business atau WhatsApp Standar yang terinstall."""
    global WA_PACKAGE, WA_MAIN_ACTIVITY
    pkgs = run_root("pm list packages")
    if WA_BUSINESS_PACKAGE in pkgs:
        WA_PACKAGE = WA_BUSINESS_PACKAGE
        WA_MAIN_ACTIVITY = f"{WA_PACKAGE}/.Main"
        log("Terdeteksi: WhatsApp Business (com.whatsapp.w4b)", "SUCCESS")
    elif WA_STANDARD_PACKAGE in pkgs:
        WA_PACKAGE = WA_STANDARD_PACKAGE
        WA_MAIN_ACTIVITY = f"{WA_PACKAGE}/.Main"
        log("Terdeteksi: WhatsApp Standar (com.whatsapp)", "SUCCESS")
    else:
        log("WhatsApp tidak ditemukan di sistem. Pastikan WhatsApp Business sudah terinstall!", "WARN")

def navigate_to_phone_input():
    """Menavigasikan dari halaman awal ke halaman input nomor WhatsApp Business."""
    for attempt in range(8):
        xml = dump_ui()
        
        # Cek apakah sudah di form input nomor
        pos, _ = find_element(xml, res_id="registration_phone")
        if pos:
            return True

        # WhatsApp Business: Tombol "Use a different number" / "Gunakan nomor lain"
        diff_pos, _ = find_element(xml, text_pattern="use a different number")
        if not diff_pos:
            diff_pos, _ = find_element(xml, text_pattern="gunakan nomor lain")
        if not diff_pos:
            diff_pos, _ = find_element(xml, text_pattern="different number")
        if diff_pos:
            log("Mengklik 'Use a different number' di WhatsApp Business...", "INFO")
            tap(diff_pos[0], diff_pos[1])
            time.sleep(2)
            continue

        # Halaman pemilihan bahasa (Language selection)
        pos, _ = find_element(xml, text_pattern="english")
        if not pos:
            pos, _ = find_element(xml, text_pattern="indonesia")
        arrow_pos, _ = find_element(xml, res_id="next_button")
        if arrow_pos:
            log("Memilih bahasa...", "INFO")
            tap(arrow_pos[0], arrow_pos[1])
            time.sleep(1.5)
            continue

        # Tombol 'Agree and continue' / 'Setuju dan lanjutkan'
        pos, _ = find_element(xml, text_pattern="agree and continue")
        if not pos:
            pos, _ = find_element(xml, text_pattern="setuju dan lanjutkan")
        if pos:
            log("Mengklik 'Agree and continue'...", "INFO")
            tap(pos[0], pos[1])
            time.sleep(2)
            continue

        # Tombol Continue / Lanjutkan pada dialog izin
        cont_pos, _ = find_element(xml, text_pattern="continue")
        if not cont_pos:
            cont_pos, _ = find_element(xml, text_pattern="lanjutkan")
        if cont_pos:
            tap(cont_pos[0], cont_pos[1])
            time.sleep(1)
            continue

        time.sleep(1)
        
    return False

def extract_country_code_and_number(nomor):
    """Mengekstrak kode negara dan nomor telepon secara dinamis untuk semua negara (+224, +258, +62, dll)."""
    clean_no = nomor.replace("+", "").replace(" ", "").replace("-", "").strip()
    if not clean_no:
        return "62", ""

    # Kode negara 1 digit: US/Canada (+1), Russia/Kazakhstan (+7)
    if clean_no.startswith("1") or clean_no.startswith("7"):
        return clean_no[:1], clean_no[1:]

    # Daftar umum kode negara 2 digit
    two_digit_ccs = {
        "20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "51", "52", "53", "54", "55", "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81", "82", "84", "86",
        "90", "91", "92", "93", "94", "95", "98"
    }
    if len(clean_no) >= 2 and clean_no[:2] in two_digit_ccs:
        return clean_no[:2], clean_no[2:]

    # Kode negara 3 digit (cth: 224 Guinea, 258 Mozambik, 234 Nigeria, dll)
    if len(clean_no) > 3:
        return clean_no[:3], clean_no[3:]

    return "62", clean_no

def input_number_and_submit(nomor):
    """Memasukkan nomor telepon ke form pendaftaran WhatsApp dengan kode negara dinamis."""
    country_code, phone_no = extract_country_code_and_number(nomor)
    log(f"Ekstraksi nomor {nomor} -> Kode Negara: +{country_code}, Nomor: {phone_no}", "INFO")

    xml = dump_ui()

    # 1. Input kode negara jika ada input field kode negara
    cc_pos, _ = find_element(xml, res_id="registration_cc")
    if not cc_pos:
        cc_pos, _ = find_element(xml, res_id="cc")
    if cc_pos:
        tap(cc_pos[0], cc_pos[1])
        time.sleep(0.3)
        # Hapus kode negara lama (misal 62)
        for _ in range(5):
            press_key(67) # KEYCODE_DEL
        time.sleep(0.2)
        type_text(country_code)
        time.sleep(0.5)

    # 2. Input nomor telepon
    xml = dump_ui() # Re-dump UI untuk memperbarui koordinat phone_pos jika ada perubahan layout
    phone_pos, _ = find_element(xml, res_id="registration_phone")
    if not phone_pos:
        phone_pos, _ = find_element(xml, res_id="phone_number")
    if not phone_pos:
        phone_pos, _ = find_element(xml, text_pattern="phone number")
    
    if phone_pos:
        tap(phone_pos[0], phone_pos[1])
        time.sleep(0.3)
        # Hapus teks nomor sebelumnya
        for _ in range(18):
            press_key(67) # KEYCODE_DEL
        time.sleep(0.2)
        type_text(phone_no)
        time.sleep(0.5)

    # 3. Klik tombol Next / Lanjut
    xml = dump_ui()
    next_pos, _ = find_element(xml, res_id="registration_submit")
    if not next_pos:
        next_pos, _ = find_element(xml, text_pattern="next")
    if not next_pos:
        next_pos, _ = find_element(xml, text_pattern="lanjut")

    if next_pos:
        log(f"Mengklik Next untuk nomor +{country_code} {phone_no}...", "INFO")
        tap(next_pos[0], next_pos[1])
    else:
        press_key(66) # Enter

    time.sleep(3)

    # 4. Tangani dialog konfirmasi "Is this the correct number?" -> Klik YES / OK
    xml_confirm = dump_ui()
    yes_pos, _ = find_element(xml_confirm, text_pattern="yes")
    if not yes_pos:
        yes_pos, _ = find_element(xml_confirm, text_pattern="ya")
    if not yes_pos:
        yes_pos, _ = find_element(xml_confirm, text_pattern="ok")
    if yes_pos:
        tap(yes_pos[0], yes_pos[1])
        time.sleep(2)

def detect_response(timeout=15):
    """
    Mendeteksi respon setelah submit nomor.
    Returns:
        "OTP_SMS"      -> Minta kode SMS
        "SKIP_DEVICE"  -> Minta verifikasi di HP / Pairing Code
        "BANNED"       -> Nomor terblokir
        "UNKNOWN"      -> Tidak dikenal
    """
    start = time.time()
    while time.time() - start < timeout:
        xml = dump_ui()
        xml_lower = xml.lower()

        # 1. Deteksi OTP SMS
        if (
            "verifying your number" in xml_lower
            or "enter 6-digit code" in xml_lower
            or "we have sent an sms" in xml_lower
            or "masukkan kode 6 digit" in xml_lower
            or "kami telah mengirimkan sms" in xml_lower
            or "resend sms" in xml_lower
        ):
            return "OTP_SMS"

        # 2. Deteksi meminta kode di HP lain / Pairing Code
        if (
            "enter code on phone" in xml_lower
            or "check your other phone" in xml_lower
            or "periksa ponsel anda yang lain" in xml_lower
            or "code on your phone" in xml_lower
        ):
            return "SKIP_DEVICE"

        # 3. Deteksi Banned / Invalid
        if (
            "is banned from using whatsapp" in xml_lower
            or "diblokir untuk menggunakan whatsapp" in xml_lower
            or "not a valid mobile number" in xml_lower
        ):
            return "BANNED"

        time.sleep(1.5)
        
    return "UNKNOWN"

def click_didnt_receive_code_and_check_timer():
    """
    Mengklik 'OK' jika ada popup warning, lalu mengklik 'Didn't receive code?'
    dan mengecek durasi timer di 'Receive new SMS' / 'Try again in X'.
    
    Returns:
        ("STOP", "Try again in < 10 mins (XX mins)")
        ("NEXT", "Try again in > 10 mins (XX hours/mins)")
        ("FAILED", "Could not detect timer")
    """
    xml = dump_ui()
    xml_lower = xml.lower()
    
    # 0. Cek jika ada popup "You tried requesting code to other phone too many times... OK"
    if "too many times" in xml_lower or "requesting code" in xml_lower or "to verify, tap" in xml_lower or "terlalu banyak" in xml_lower:
        log("Terdeteksi popup warning 'Requesting code too many times'. Mengklik OK...", "INFO")
        ok_pos, _ = find_element(xml, text_pattern="ok")
        if not ok_pos:
            ok_pos, _ = find_element(xml, res_id="button1")
        if ok_pos:
            tap(ok_pos[0], ok_pos[1])
            time.sleep(1.5)
            xml = dump_ui()
            xml_lower = xml.lower()
    
    # 1. Klik "Didn't receive code?"
    log("Mengklik 'Didn't receive code?'...", "INFO")
    pos, _ = find_element(xml, text_pattern="didn't receive code")
    if not pos:
        pos, _ = find_element(xml, text_pattern="didn’t receive code")
    if not pos:
        pos, _ = find_element(xml, text_pattern="tidak menerima kode")
    if not pos:
        pos, _ = find_element(xml, text_pattern="receive code")

    if pos:
        tap(pos[0], pos[1])
        time.sleep(2)
    else:
        log("Tombol 'Didn't receive code?' tidak ditemukan di layar. Analisis layar langsung...", "WARN")

    # 2. Ambil snapshot UI terbaru setelah klik (termasuk bottom sheet 'Choose how to verify')
    xml_sheet = dump_ui()
    xml_sheet_lower = xml_sheet.lower()

    # 3. Analisis Timer dari Teks XML secara langsung (Sangat Akurat)
    # Cek Jam (hour / hrs / jam) -> Pasti > 10 menit (cth: 7 hours, 19 hours)
    match_hour = re.search(r'(\d+)\s*(hour|hrs|hr|jam)', xml_sheet_lower)
    if match_hour:
        hrs = int(match_hour.group(1))
        log(f"--> Timer terdeteksi: {hrs} jam (di atas 10 menit). Lanjut ke nomor berikutnya!", "WARN")
        return "NEXT", f"Timer {hrs} jam (> 10 menit)"

    # Cek Menit (minute / min / menit)
    match_min = re.search(r'(\d+)\s*(minute|minutes|min|menit)', xml_sheet_lower)
    if match_min:
        mins = int(match_min.group(1))
        if mins < 10:
            log(f"--> Timer terdeteksi: {mins} menit (di bawah 10 menit). STOP SEMUA PROSES!", "SUCCESS")
            return "STOP", f"Timer {mins} menit (< 10 menit)"
        else:
            log(f"--> Timer terdeteksi: {mins} menit (di atas 10 menit). Lanjut ke nomor berikutnya!", "WARN")
            return "NEXT", f"Timer {mins} menit (>= 10 menit)"

    # Cek Detik (second / sec / detik) -> < 10 menit
    match_sec = re.search(r'(\d+)\s*(second|seconds|sec|detik)', xml_sheet_lower)
    if match_sec:
        secs = int(match_sec.group(1))
        log(f"--> Timer terdeteksi: {secs} detik (di bawah 10 menit). STOP SEMUA PROSES!", "SUCCESS")
        return "STOP", f"Timer {secs} detik (< 10 menit)"

    # Jika ada indikasi "try again" atau "coba lagi" tapi angka tidak terurai -> Anggap > 10 menit (Skip)
    if "try again" in xml_sheet_lower or "coba lagi" in xml_sheet_lower:
        log("--> Terdeteksi pesan 'try again/coba lagi'. Anggap timer > 10 menit. Lanjut!", "WARN")
        return "NEXT", "Timer terdeteksi (try again/coba lagi) > 10 menit"

    # Jika tidak ada timer sama sekali dan tombol SMS siap/tersedia
    if "receive new sms" in xml_sheet_lower or "resend sms" in xml_sheet_lower or "terima sms" in xml_sheet_lower:
        log("--> SMS dapat dikirim sekarang (tanpa timer / < 10 menit). STOP SEMUA PROSES!", "SUCCESS")
        return "STOP", "SMS dapat dikirim sekarang"

    return "NEXT", "Timer tidak terdeteksi (Default skip)"

def click_wrong_number():
    """Mengklik 'Wrong number?' di layar verifikasi untuk kembali ke form input nomor."""
    log("Mengklik 'Wrong number?' untuk lanjut ke nomor berikutnya...", "INFO")
    
    # 1. Tutup bottom sheet jika terbuka dengan menekan area atas layar
    tap(540, 150)
    time.sleep(0.5)
    press_key(4) # Back key jika masih terbuka
    time.sleep(1)

    # 2. Cari & klik "Wrong number?" di layar verifikasi
    for attempt in range(3):
        xml = dump_ui()
        pos, _ = find_element(xml, text_pattern="wrong number")
        if not pos:
            pos, _ = find_element(xml, text_pattern="salah nomor")
        if not pos:
            pos, _ = find_element(xml, text_pattern="wrong")

        if pos:
            log(f"Mengklik 'Wrong number?' di koordinat {pos}...", "INFO")
            tap(pos[0], pos[1])
            time.sleep(2)
            # Cek apakah sudah kembali ke halaman input
            xml_check = dump_ui()
            if "phone" in xml_check.lower() or "nomor" in xml_check.lower() or "registration_phone" in xml_check:
                return True
        else:
            # Fallback beberapa titik koordinat biru "Wrong number?" yang umum di HP Android
            log(f"Mencoba tap koordinat fallback 'Wrong number?' (Attempt {attempt+1})...", "INFO")
            tap(540, 280)
            time.sleep(1)
            tap(540, 350)
            time.sleep(1.5)
            xml_check = dump_ui()
            if "phone" in xml_check.lower() or "nomor" in xml_check.lower():
                return True

    log("Gagal mengklik 'Wrong number?'. Melakukan reset WhatsApp agar kembali ke form input...", "WARN")
    reset_whatsapp()
    return True

def main():
    print("\n" + "=" * 60)
    print("   WHATSAPP CLOUDPHONE AUTO LOGIN (TERMUX ROOT)")
    print("=" * 60 + "\n")

    if not check_root():
        sys.exit(1)

    detect_whatsapp_package()

    nomor_file = "nomor.txt"
    if not os.path.exists(nomor_file):
        log(f"File '{nomor_file}' tidak ditemukan!", "ERROR")
        return

    with open(nomor_file, "r", encoding="utf-8") as f:
        numbers = [line.strip().replace(" ", "").replace("-", "") for line in f if line.strip() and not line.startswith("#")]

    log(f"Berhasil memuat {len(numbers)} nomor dari {nomor_file}.", "SUCCESS")

    open_whatsapp()
    time.sleep(2)

    idx = 0
    while idx < len(numbers):
        nomor = numbers[idx]
        print("\n" + "-" * 55)
        log(f"[{idx + 1}/{len(numbers)}] Memproses Nomor: {nomor}", "INFO")
        print("-" * 55)

        # 1. Navigasikan ke input form
        if not navigate_to_phone_input():
            log("Mereset WhatsApp untuk kembali ke form input...", "WARN")
            reset_whatsapp()
            if not navigate_to_phone_input():
                log(f"Gagal menuju form input. Lewati nomor {nomor}.", "ERROR")
                record_result(nomor, "FAILED", "Gagal navigasi form input")
                idx += 1
                continue

        # 2. Input nomor
        input_number_and_submit(nomor)

        # 3. Deteksi apakah masuk ke layar 'Verifying your number' atau 'Banned'
        resp = detect_response(timeout=12)

        if resp == "BANNED":
            log(f"--> [BANNED] Nomor {nomor} terblokir / tidak valid.", "ERROR")
            record_result(nomor, "BANNED", "Nomor terblokir oleh WhatsApp")
            press_key(66) # Enter / OK
            time.sleep(1)
            press_key(4)  # Back
            idx += 1
            continue

        elif resp == "SKIP_DEVICE":
            log("--> Terdeteksi meminta kode di HP lain.", "WARN")
            record_result(nomor, "SKIPPED", "Minta verifikasi di HP / Device lain")
            press_key(4) # Back
            time.sleep(1)
            idx += 1
            continue

        # 4. Jika masuk ke layar Verifikasi SMS -> Klik 'Didn't receive code?'
        action_type, detail_msg = click_didnt_receive_code_and_check_timer()

        if action_type == "STOP":
            # KONDISI A: Timer < 10 menit -> BERHENTI SEMUA PROSES
            record_result(nomor, "STOP_OTP", f"SMS < 10 menit ({detail_msg})")
            
            print("\n" + "#" * 65)
            print(" [!] PERHATIAN: TIMER SMS DIBAWAH 10 MENIT / BISA DITERIMA!")
            print(f"     Nomor: {nomor}")
            print(f"     Detail: {detail_msg}")
            print("     Semua proses otomatis dihentikan sementara.")
            print("     Silakan masukkan OTP SMS secara manual di WhatsApp.")
            print("#" * 65)

            while True:
                cmd = input("\nKetik 'next' untuk lanjut ke nomor berikutnya, atau 'quit' untuk berhenti: ").strip().lower()
                if cmd in ('next', 'lanjut', ''):
                    log("Melanjutkan ke nomor berikutnya...", "INFO")
                    click_wrong_number()
                    idx += 1
                    break
                elif cmd in ('quit', 'q', 'exit'):
                    log("Proses dihentikan oleh user.", "WARN")
                    return
                else:
                    print("Ketik 'next' atau 'quit'.")

        elif action_type == "NEXT":
            # KONDISI B: Timer > 10 menit (misal 19 hours) -> KLIK WRONG NUMBER & LANJUT
            log(f"--> [LANJUT] {detail_msg}. Klik 'Wrong number' dan beralih ke nomor berikutnya.", "WARN")
            record_result(nomor, "SKIPPED_TIMER", f"Timer > 10 menit ({detail_msg})")
            click_wrong_number()
            idx += 1

        else:
            log(f"--> Gagal membaca timer respon untuk nomor {nomor}. Lanjut nomor berikutnya...", "WARN")
            record_result(nomor, "UNKNOWN", detail_msg)
            click_wrong_number()
            idx += 1

    print("\n" + "=" * 60)
    print(" SEMUA NOMOR SELESAI DIPROSES!")
    print(" Laporan hasil tersimpan di file: result.txt")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
