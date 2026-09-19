"""
WhatsApp Desktop Auto Login Tool
================================
Tool otomatisasi untuk memproses daftar nomor WhatsApp di WhatsApp Desktop.

Fitur:
- Membaca nomor dari file nomor.txt satu per satu.
- Otomatis input nomor ke WhatsApp Desktop.
- Jika meminta Pairing Code ("Enter code on phone") -> OTOMATIS SKIP ke nomor berikutnya.
- Jika meminta OTP SMS -> BERHENTI SEMUA PROSES, menunggu input manual user sampai user meminta lanjut.
- Mencatat seluruh log dan hasil ke file result.txt dan wa_login.log.
"""

import sys
import os
import time
import ctypes
import ctypes.wintypes
from datetime import datetime
from PIL import Image
import winocr
import pyperclip
import pyautogui
import winsound

# Win32 API handles
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Set thread desktop ke 'default' agar dapat mengakses window di desktop interaktif
def attach_to_default_desktop():
    try:
        d = user32.OpenDesktopW('default', 0, False, 0x01FF)
        if d:
            user32.SetThreadDesktop(d)
    except Exception as e:
        print(f"[WARN] Failed to attach to default desktop: {e}")

attach_to_default_desktop()

class WhatsAppBot:
    def __init__(self, nomor_file="nomor.txt", result_file="result.txt", log_file="wa_login.log"):
        self.nomor_file = nomor_file
        self.result_file = result_file
        self.log_file = log_file
        self.hwnd = None
        self.total_processed = 0
        self.total_skipped = 0
        self.total_otp = 0
        self.total_failed = 0

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

    def record_result(self, nomor, status, detail=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"{timestamp} | {nomor} | {status} | {detail}\n"
        try:
            with open(self.result_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            self.log(f"Gagal mencatat hasil: {e}", "ERROR")

    def find_whatsapp_window(self):
        """Mencari window WhatsApp Desktop yang aktif."""
        attach_to_default_desktop()
        wins = []
        cb = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)(
            lambda h, l: (wins.append(h), True)[1]
        )
        user32.EnumDesktopWindows(0, cb, 0)
        for h in wins:
            if user32.IsWindowVisible(h):
                l = user32.GetWindowTextLengthW(h)
                b = ctypes.create_unicode_buffer(l + 1)
                user32.GetWindowTextW(h, b, l + 1)
                cls_b = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(h, cls_b, 256)
                if b.value == 'WhatsApp' and cls_b.value in ('WinUIDesktopWin32WindowClass', 'Chrome_WidgetWin_1'):
                    return h
        return None

    def ensure_whatsapp_running(self):
        """Memastikan WhatsApp Desktop terbuka dan aktif."""
        self.hwnd = self.find_whatsapp_window()
        if not self.hwnd:
            self.log("WhatsApp Desktop belum terbuka. Membuka aplikasi WhatsApp Desktop...", "INFO")
            os.system('powershell -Command "Start-Process \'shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App\'"')
            for _ in range(15):
                time.sleep(1)
                self.hwnd = self.find_whatsapp_window()
                if self.hwnd:
                    break

        if not self.hwnd:
            self.log("Gagal mendeteksi WhatsApp Desktop. Pastikan aplikasi terinstall.", "ERROR")
            return False

        # Maximize dan bawa ke depan
        user32.ShowWindow(self.hwnd, 3)  # SW_MAXIMIZE
        time.sleep(0.3)
        user32.SetForegroundWindow(self.hwnd)
        time.sleep(0.5)
        self.log(f"WhatsApp Desktop aktif (HWND: {self.hwnd})", "SUCCESS")
        return True

    def capture_screen(self):
        """Menangkap screenshot window WhatsApp secara langsung."""
        if not self.hwnd:
            return None, None
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        w = max(1, rect.right - rect.left)
        h = max(1, rect.bottom - rect.top)

        hdc_win = user32.GetDC(self.hwnd)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        gdi32.SelectObject(hdc_mem, hbmp)
        user32.PrintWindow(self.hwnd, hdc_mem, 2)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', ctypes.wintypes.DWORD), ('biWidth', ctypes.wintypes.LONG), ('biHeight', ctypes.wintypes.LONG),
                ('biPlanes', ctypes.wintypes.WORD), ('biBitCount', ctypes.wintypes.WORD), ('biCompression', ctypes.wintypes.DWORD),
                ('biSizeImage', ctypes.wintypes.DWORD), ('biXPelsPerMeter', ctypes.wintypes.LONG), ('biYPelsPerMeter', ctypes.wintypes.LONG),
                ('biClrUsed', ctypes.wintypes.DWORD), ('biClrImportant', ctypes.wintypes.DWORD),
            ]
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
        img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)

        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(self.hwnd, hdc_win)
        return img.convert('RGB'), rect

    def get_ocr(self):
        """Mengambil screenshot dan melakukan OCR."""
        img, rect = self.capture_screen()
        if not img:
            return "", [], rect, img
        try:
            res = winocr.recognize_pil_sync(img)
            return res.get('text', ''), res.get('lines', []), rect, img
        except Exception as e:
            self.log(f"OCR error: {e}", "WARN")
            return "", [], rect, img

    def click_window_coords(self, rel_x, rel_y, rect):
        """Klik koordinat relatif terhadap window WhatsApp."""
        click_x = int(rect.left + rel_x)
        click_y = int(rect.top + rel_y)
        user32.SetForegroundWindow(self.hwnd)
        time.sleep(0.1)
        user32.SetCursorPos(click_x, click_y)
        time.sleep(0.1)
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.1)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def find_text_coords(self, lines, search_terms):
        """Mencari koordinat tepat dari kata atau frasa hasil OCR."""
        for term in search_terms:
            term_lower = term.lower().strip()
            # 1. Coba pencarian per KATA tunggal
            for line in lines:
                for w in line['words']:
                    w_text = w['text'].lower().strip()
                    if term_lower in w_text or w_text == term_lower or term_lower in w_text.replace('(', '').replace(')', ''):
                        br = w['bounding_rect']
                        return (br['x'] + br['width'] / 2, br['y'] + br['height'] / 2)

            # 2. Coba pencarian frasa dalam baris
            for line in lines:
                line_text = line['text'].lower()
                if term_lower in line_text:
                    # Ambil kata-kata yang cocok dalam baris
                    words = line['words']
                    matching_words = [w for w in words if any(part in w['text'].lower() for part in term_lower.split())]
                    if matching_words:
                        x = min(w['bounding_rect']['x'] for w in matching_words)
                        y = min(w['bounding_rect']['y'] for w in matching_words)
                        w_box = sum(w['bounding_rect']['width'] for w in matching_words)
                        h_box = max(w['bounding_rect']['height'] for w in matching_words)
                        return (x + w_box / 2, y + h_box / 2)
        return None

    def navigate_to_phone_input(self):
        """Memastikan WhatsApp berada di halaman 'Enter phone number'."""
        max_attempts = 5
        for attempt in range(max_attempts):
            text, lines, rect, _ = self.get_ocr()
            text_lower = text.lower()

            # Jika sudah di halaman input nomor
            if "enter phone number" in text_lower or "select a country" in text_lower:
                self.log("Sudah di halaman input nomor telepon.", "INFO")
                return True

            # Jika di halaman Welcome ("Log in" / "Get started")
            if "welcome to whatsapp" in text_lower or "message privately" in text_lower:
                self.log("Menemukan tombol 'Log in', mengklik...", "INFO")
                coords = self.find_text_coords(lines, ["Log in", "Get started"])
                if coords:
                    self.click_window_coords(coords[0], coords[1], rect)
                    time.sleep(2)
                    continue

            # Jika di halaman Scan QR Code ("Log in with phone number")
            if "log in with phone number" in text_lower or "with phone number" in text_lower:
                self.log("Mengklik opsi 'Log in with phone number'...", "INFO")
                coords = self.find_text_coords(lines, ["Log in with phone number", "phone number"])
                if coords:
                    self.click_window_coords(coords[0], coords[1], rect)
                    time.sleep(2)
                    continue

            # Jika di halaman Pairing Code ("Enter code on phone")
            if "enter code on phone" in text_lower or "code on your phone" in text_lower:
                self.log("Berada di halaman pairing code, kembali ke halaman input...", "INFO")
                # Klik tombol (edit) jika ada
                edit_coords = self.find_text_coords(lines, ["(edit)", "edit"])
                if edit_coords:
                    self.click_window_coords(edit_coords[0], edit_coords[1], rect)
                else:
                    # Klik tombol panah Back di kiri atas kartu
                    self.click_window_coords(758, 380, rect)
                time.sleep(2)
                continue

            time.sleep(1)

        self.log("Gagal menavigasi ke halaman input nomor telepon.", "ERROR")
        return False

    def input_number_and_submit(self, nomor):
        """Memasukkan nomor telepon dan klik Next."""
        text, lines, rect, _ = self.get_ocr()

        # Lokasi box input phone number (di kanan kode negara atau koordinat default)
        input_pos = (920, 535)
        for line in lines:
            for w in line['words']:
                if '+' in w['text']:
                    bx = w['bounding_rect']['x']
                    by = w['bounding_rect']['y']
                    input_pos = (bx + 80, by + 10)
                    break

        self.log(f"Menginput nomor: {nomor}", "INFO")
        self.click_window_coords(input_pos[0], input_pos[1], rect)
        time.sleep(0.2)

        # Bersihkan input lama
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.press('backspace')
        time.sleep(0.1)

        # Paste nomor lengkap
        formatted_no = nomor if nomor.startswith('+') else f"+{nomor}"
        pyperclip.copy(formatted_no)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.4)

        # Klik tombol Next atau tekan Enter
        next_coords = self.find_text_coords(lines, ["Next"])
        if next_coords:
            self.click_window_coords(next_coords[0], next_coords[1], rect)
        else:
            pyautogui.press('enter')

        time.sleep(1)

    def wait_and_detect_response(self, nomor, timeout_seconds=15):
        """
        Mendeteksi respon dari WhatsApp Desktop setelah memasukkan nomor.
        Returns:
            "PAIRING_CODE" -> jika meminta code di HP
            "OTP_SMS"      -> jika meminta kode OTP SMS
            "INVALID"      -> jika nomor salah/invalid/error
            "UNKNOWN"      -> tidak dapat ditentukan
        """
        start_time = time.time()
        self.log("Menunggu respon dari WhatsApp Desktop...", "INFO")

        while time.time() - start_time < timeout_seconds:
            time.sleep(1.5)
            text, lines, rect, _ = self.get_ocr()
            text_lower = text.lower()

            # 1. Deteksi "Enter code on phone" (Pairing Code)
            if (
                "enter code on phone" in text_lower
                or "code on your phone" in text_lower
                or "linking whatsapp account" in text_lower
                or "link with phone number instead" in text_lower
            ):
                return "PAIRING_CODE"

            # 2. Deteksi OTP SMS
            # WhatsApp menampilkan teks seperti: "Enter verification code", "We sent an SMS", "Enter the 6-digit code", "Check your phone for SMS"
            if (
                "verification code" in text_lower
                or "sent an sms" in text_lower
                or "6-digit code" in text_lower
                or "enter the code" in text_lower
                or "resend sms" in text_lower
            ):
                return "OTP_SMS"

            # 3. Deteksi error / nomor tidak valid
            if (
                "not valid" in text_lower
                or "invalid phone number" in text_lower
                or "please check your phone number" in text_lower
                or "something went wrong" in text_lower
            ):
                return "INVALID"

        return "UNKNOWN"

    def back_to_number_input(self):
        """Kembali ke halaman input nomor setelah muncul Pairing Code (Enter code on phone)."""
        self.log("Mengklik Back / (edit) untuk kembali ke input nomor...", "INFO")
        for attempt in range(3):
            text, lines, rect, _ = self.get_ocr()
            text_lower = text.lower()

            # Jika sudah kembali ke halaman input nomor
            if "enter phone number" in text_lower or "select a country" in text_lower:
                self.log("Berhasil kembali ke halaman input nomor.", "INFO")
                return True

            # 1. Coba klik link "(edit)" jika terdeteksi
            edit_coords = self.find_text_coords(lines, ["(edit)", "edit"])
            if edit_coords:
                self.log(f"Menemukan tombol (edit) di koordinat {edit_coords}, mengklik...", "INFO")
                self.click_window_coords(edit_coords[0], edit_coords[1], rect)
                time.sleep(2)
                continue

            # 2. Coba cari judul "Enter code on phone" dan klik tombol panah Back di sebelah kirinya
            title_coords = self.find_text_coords(lines, ["Enter code on phone", "code on phone"])
            if title_coords:
                # Tombol panah ← berada di sebelah kiri judul
                back_x = title_coords[0] - 165
                back_y = title_coords[1]
                self.log(f"Menemukan judul, mengklik panah Back ← di ({back_x}, {back_y})...", "INFO")
                self.click_window_coords(back_x, back_y, rect)
                time.sleep(2)
                continue

            # 3. Fallback: klik koordinat panah Back standar di kiri atas kartu WhatsApp
            self.log("Mencoba klik tombol panah Back kiri atas...", "INFO")
            self.click_window_coords(758, 380, rect)
            time.sleep(1.5)

        return False

    def run(self):
        print("\n" + "=" * 65)
        print("         WHATSAPP DESKTOP AUTO LOGIN TOOL v1.0")
        print("=" * 65)
        print(" Aturan Alur:")
        print(" • Minta Code Lewat HP (Pairing Code) -> OTOMATIS SKIP ke nomor berikutnya")
        print(" • Minta OTP SMS -> PROSES BERHENTI, tunggu input manual user")
        print("=" * 65 + "\n")

        if not os.path.exists(self.nomor_file):
            self.log(f"File '{self.nomor_file}' tidak ditemukan!", "ERROR")
            print(f"Silakan buat file '{self.nomor_file}' dan isi dengan nomor telepon (satu per baris).")
            return

        with open(self.nomor_file, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()

        numbers = []
        for line in raw_lines:
            n = line.strip().replace(" ", "").replace("-", "")
            if n and not n.startswith("#"):
                numbers.append(n)

        if not numbers:
            self.log(f"Tidak ada nomor di dalam file '{self.nomor_file}'.", "WARN")
            return

        self.log(f"Berhasil memuat {len(numbers)} nomor dari '{self.nomor_file}'.", "SUCCESS")
        for idx, num in enumerate(numbers, 1):
            print(f"  {idx}. {num}")
        print()

        if not self.ensure_whatsapp_running():
            return

        print("\nPastikan WhatsApp Desktop siap. Tool akan mulai memproses nomor.")
        time.sleep(2)

        idx = 0
        while idx < len(numbers):
            nomor = numbers[idx]
            self.total_processed += 1
            print("\n" + "-" * 60)
            self.log(f"[{idx + 1}/{len(numbers)}] Memproses nomor: {nomor}", "INFO")
            print("-" * 60)

            # 1. Pastikan di halaman input nomor
            if not self.navigate_to_phone_input():
                self.log(f"Melewati nomor {nomor} karena gagal navigasi ke input nomor.", "ERROR")
                self.record_result(nomor, "FAILED", "Gagal navigasi ke halaman input")
                self.total_failed += 1
                idx += 1
                continue

            # 2. Input nomor telepon
            self.input_number_and_submit(nomor)

            # 3. Deteksi respon
            response = self.wait_and_detect_response(nomor, timeout_seconds=15)

            if response == "PAIRING_CODE":
                # KONDISI 1: SKIP KE NOMOR BERIKUTNYA
                self.log(f"--> Terdeteksi PAIRING CODE (Enter code on phone).", "WARN")
                self.log(f"--> [AUTO SKIP] Melewati nomor {nomor} dan lanjut ke nomor berikutnya...", "SUCCESS")
                self.record_result(nomor, "SKIPPED", "Meminta code lewat handphone (Pairing Code)")
                self.total_skipped += 1

                # Kembali ke halaman input untuk nomor selanjutnya
                self.back_to_number_input()
                idx += 1
                time.sleep(2)

            elif response == "OTP_SMS":
                # KONDISI 2: BERHENTI SEMUA PROSES, TUNGGU USER MANUAL
                self.total_otp += 1
                self.record_result(nomor, "OTP_SMS", "Meminta OTP SMS - Proses dihentikan untuk input manual")

                # Bunyikan alarm notifikasi
                try:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass

                print("\n" + "#" * 65)
                print(" [!] PERHATIAN: NOMOR MEMINTA OTP SMS!")
                print(f"     Nomor Telepon: {nomor}")
                print("     Semua proses otomatis dihentikan.")
                print("     Silakan masukkan kode OTP SMS secara manual di WhatsApp Desktop.")
                print("#" * 65)

                while True:
                    cmd = input("\nKetik 'next' untuk lanjut ke nomor berikutnya, atau 'quit' untuk berhenti: ").strip().lower()
                    if cmd in ('next', 'lanjut', ''):
                        self.log("User mengonfirmasi lanjut ke nomor berikutnya.", "INFO")
                        idx += 1
                        break
                    elif cmd in ('quit', 'exit', 'q', 'berhenti'):
                        self.log("Proses dihentikan oleh user.", "WARN")
                        self.print_summary()
                        return
                    else:
                        print("Perintah tidak dikenali. Ketik 'next' untuk lanjut atau 'quit' untuk keluar.")

            elif response == "INVALID":
                self.log(f"Nomor {nomor} tidak valid atau terjadi kesalahan jaringan.", "ERROR")
                self.record_result(nomor, "INVALID", "Nomor tidak valid atau error")
                self.total_failed += 1
                # Tekan OK atau kembali
                pyautogui.press('enter')
                time.sleep(1)
                idx += 1

            else:
                self.log(f"Respon tidak dikenali untuk nomor {nomor}. Mengambil screenshot debug...", "WARN")
                _, _, _, dbg_img = self.get_ocr()
                if dbg_img:
                    dbg_img.save(f"debug_unknown_{nomor}.png")
                self.record_result(nomor, "UNKNOWN", "Respon tidak dapat diidentifikasi")
                self.total_failed += 1
                self.back_to_number_input()
                idx += 1

        self.print_summary()

    def print_summary(self):
        print("\n" + "=" * 65)
        print("                     RINGKASAN HASIL")
        print("=" * 65)
        print(f" Total Nomor Diproses   : {self.total_processed}")
        print(f" Skipped (Code on Phone): {self.total_skipped}")
        print(f" Meminta OTP SMS        : {self.total_otp}")
        print(f" Gagal / Invalid        : {self.total_failed}")
        print("-" * 65)
        print(f" Detail log tersimpan di : {self.log_file}")
        print(f" Laporan hasil di        : {self.result_file}")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    bot = WhatsAppBot()
    bot.run()
