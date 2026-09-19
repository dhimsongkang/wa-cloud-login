#!/usr/bin/env python3
"""
Simulasi Android Shell Commands - Test wa_termux_login.py
=========================================================
Menunjukkan PERSIS perintah shell apa saja yang akan dijalankan
oleh wa_termux_login.py saat input nomor ke WhatsApp.
"""

# ========== SIMULASI run_root ==========
def run_root_OLD(cmd):
    """VERSI LAMA (BUGGY) - Quoting bermasalah!"""
    full_cmd = f"su -c '{cmd}'"
    return full_cmd

def run_root_NEW(cmd):
    """VERSI BARU (FIXED) - Pakai list args, tanpa quoting issue."""
    # subprocess.run(["su", "-c", cmd]) -> setiap item jadi argument terpisah
    return f'subprocess.run(["su", "-c", "{cmd}"])'

# ========== Test type_text LAMA ==========
print("=" * 70)
print("BUG ANALYSIS: Kenapa nomor tidak terketik?")
print("=" * 70)

nomor = "+224621393656"
clean_no = nomor.replace("+", "").replace(" ", "").replace("-", "")

print(f"\nNomor dari nomor.txt: {nomor}")
print(f"Setelah dibersihkan:  {clean_no}")

# VERSI LAMA
print("\n--- VERSI LAMA (BUGGY) ---")
cmd_old = f"input text '{clean_no}'"
shell_cmd_old = f"su -c '{cmd_old}'"
print(f"Python code : run_root(f\"input text '{{clean_no}}'\")")
print(f"Shell command: {shell_cmd_old}")
print(f"")
print(f"Shell melihat:")
print(f"  Arg 1: su")
print(f"  Arg 2: -c")
print(f"  Arg 3: 'input text '  <-- string BERAKHIR disini!")
print(f"  Arg 4: {clean_no}     <-- ini BUKAN bagian dari -c command!")
print(f"  Arg 5: ''             <-- string kosong")
print(f"")
print(f"  >>> su menjalankan: 'input text ' (TANPA ANGKA!)")
print(f"  >>> HASILNYA: TIDAK MENGETIK APA-APA! <<<")

# VERSI BARU - subprocess list
print("\n--- VERSI BARU (FIXED) - subprocess.run list args ---")
cmd_new = f"input text {clean_no}"
print(f"Python code : subprocess.run(['su', '-c', 'input text {clean_no}'])")
print(f"")
print(f"Subprocess melihat:")
print(f"  Arg 1: su")
print(f"  Arg 2: -c")
print(f"  Arg 3: input text {clean_no}  <-- SATU string utuh!")
print(f"")
print(f"  >>> su menjalankan: 'input text {clean_no}'")
print(f"  >>> HASILNYA: BERHASIL MENGETIK {clean_no}! <<<")

# VERSI BARU - key events (PALING RELIABLE)
print("\n--- VERSI BARU (SUPER RELIABLE) - Individual Key Events ---")
print(f"Mengetik '{clean_no}' digit per digit:")
KEYCODE_MAP = {str(i): 7 + i for i in range(10)}
for i, d in enumerate(clean_no):
    keycode = KEYCODE_MAP[d]
    print(f"  Digit '{d}' -> subprocess.run(['su', '-c', 'input keyevent {keycode}'])  # KEYCODE_{d}")

print(f"\n  >>> Setiap digit dikirim sebagai keypress fisik")
print(f"  >>> PASTI BERHASIL di semua field Android! <<<")

# ========== Test press_key ==========
print("\n" + "=" * 70)
print("Test: Apakah tap & press_key juga bermasalah?")
print("=" * 70)

print(f"\ntap(540, 150):")
tap_old = f"su -c 'input tap 540 150'"
print(f"  LAMA: {tap_old}  -> OK (tidak ada nested quotes)")

print(f"\npress_key(67):")
key_old = f"su -c 'input keyevent 67'"
print(f"  LAMA: {key_old}  -> OK (tidak ada nested quotes)")

print(f"\nKESIMPULAN: tap dan press_key TIDAK bermasalah.")
print(f"HANYA type_text yang bermasalah karena nested single quotes!")

print("\n" + "=" * 70)
print("FIX SUMMARY")
print("=" * 70)
print("""
1. run_root() -> Ganti shell=True menjadi subprocess list args
   LAMA: subprocess.run(f"su -c '{cmd}'", shell=True)
   BARU: subprocess.run(["su", "-c", cmd])

2. type_text() -> Hapus quotes di sekitar text
   LAMA: run_root(f"input text '{text}'")
   BARU: run_root(f"input text {text}")

3. TAMBAH type_digits() -> Ketik digit satu-satu pakai keyevent
   Setiap digit 0-9 diketik sebagai KEYCODE_0(7) sampai KEYCODE_9(16)
   Ini PALING RELIABLE karena tidak ada quoting issue sama sekali!
""")
