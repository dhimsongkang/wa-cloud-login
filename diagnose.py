#!/usr/bin/env python3
"""
Diagnostic Script untuk WhatsApp Cloudphone Termux
Mengetes akses root, screen resolution, UI dump, resource-id, dan input typing.
"""

import subprocess
import os
import re
import sys
import xml.etree.ElementTree as ET

def run_cmd(cmd):
    p = subprocess.run(["su", "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.stdout.strip(), p.stderr.strip(), p.returncode

print("=" * 60)
print("   DIAGNOSTIC WHATSAPP TERMUX")
print("=" * 60)

# 1. Cek Root
print("\n[1] Memeriksa akses ROOT (su)...")
out, err, code = run_cmd("id")
print(f"    Return code: {code}")
print(f"    Stdout: {out}")
if err:
    print(f"    Stderr: {err}")
if "uid=0" not in out:
    print("    [!] Akses ROOT GAGAL! Pastikan izin Superuser sudah aktif.")
    sys.exit(1)
print("    [+] Root OK!")

# 2. Cek Ukuran Layar (Screen Resolution)
print("\n[2] Memeriksa resolusi layar (wm size)...")
out, err, _ = run_cmd("wm size")
print(f"    Resolusi Layar: {out}")

# 3. Cek UI Automator Dump ke /data/local/tmp/
print("\n[3] Menguji UI Automator dump...")
dump_path = "/data/local/tmp/wa_diag.xml"
out, err, code = run_cmd(f"uiautomator dump {dump_path} && chmod 777 {dump_path}")
print(f"    Dump command result: code={code}")
if out:
    print(f"    Stdout: {out}")
if err:
    print(f"    Stderr: {err}")

# Baca XML
out_xml, _, _ = run_cmd(f"cat {dump_path}")
print(f"    Ukuran file XML: {len(out_xml)} karakter")

if len(out_xml) < 50:
    print("    [!] UI Automator GAGAL menghasilkan XML tampilan layar!")
else:
    print("    [+] UI Automator BERHASIL dump XML.")
    
    # 4. Cari Elemen Input / EditText di XML
    print("\n[4] Menganalisis elemen input pada layar saat ini:")
    try:
        root = ET.fromstring(out_xml)
        found_inputs = []
        for node in root.iter("node"):
            cls = node.get("class", "")
            res = node.get("resource-id", "")
            text = node.get("text", "")
            bounds = node.get("bounds", "")
            
            # Cek jika ini EditText atau punya kata phone/cc/code
            if "edittext" in cls.lower() or "phone" in res.lower() or "cc" in res.lower():
                found_inputs.append((res, text, bounds, cls))
                print(f"    -> Ditemukan Elemen Input:")
                print(f"       Resource ID : {res}")
                print(f"       Class       : {cls}")
                print(f"       Text        : '{text}'")
                print(f"       Bounds      : {bounds}")
                
        if not found_inputs:
            print("    [!] Tidak ditemukan elemen EditText di layar saat ini.")
            print("    Daftar teks yang terlihat di layar:")
            for node in root.iter("node"):
                t = node.get("text", "")
                if t:
                    print(f"       - '{t}' ({node.get('bounds')})")
        else:
            # 5. Uji Coba Tap & Ketik ke elemen input pertama yang ditemukan
            target_res, _, bounds_str, _ = found_inputs[-1]  # biasanya phone field
            match = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
            if len(match) == 2:
                cx = (int(match[0][0]) + int(match[1][0])) // 2
                cy = (int(match[0][1]) + int(match[1][1])) // 2
                print(f"\n[5] Mencoba TEST TAP & KETIK ke target: {target_res} di ({cx}, {cy})...")
                run_cmd(f"input tap {cx} {cy}")
                print(f"    Tap di ({cx}, {cy}) dikirim.")
                
                print("    Mengirim angka test '12345'...")
                # Coba input text langsung
                run_cmd("input text 12345")
                print("    [+] Test selesai! Periksa apakah angka '12345' muncul di layar WhatsApp.")
    except Exception as e:
        print(f"    Error parsing XML: {e}")

print("\n" + "=" * 60)
print("Selesai. Silakan kirimkan hasil output di atas ke chat.")
print("=" * 60)
