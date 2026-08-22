# -*- coding: utf-8 -*-
"""
check_suspend_fields.py — Periksa semua kolom di suspend untuk menemukan
informasi yang bisa membedakan bulan/periode tanpa rule baru.
Jalankan: python check_suspend_fields.py
"""
import sys, io, re, os
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")

def norm(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().upper())

def load_pkl(path):
    cache = path + ".cache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        data, header = pd.read_pickle(cache)
        return pd.DataFrame(data, columns=header)
    return pd.read_excel(path)

SEP = "=" * 70

print(f"\n{SEP}")
print("  CEK KOLOM SUSPEND — info apa yang tersedia per baris?")
print(SEP)

df = load_pkl(SUSPEND_FILE)
print(f"\nTotal rows: {len(df):,}")
print(f"Total cols: {len(df.columns)}")
print(f"\nSEMUA kolom:")
for c in df.columns:
    print(f"  {c}")

# Target polis yang paling bermasalah
TARGET_POLIS = "131030824100000013"

polis_cols = [c for c in df.columns if str(c).lower().startswith("clean polis")]
mask = pd.Series(False, index=df.index)
for col in polis_cols + ["polis_ori", "FAC_POLICY_NO", "CLSDT_POLICY_NO"]:
    if col in df.columns:
        mask |= df[col].astype(str).str.upper().str.strip() == TARGET_POLIS

sub = df[mask].head(20)

if sub.empty:
    print(f"\n[!] Polis {TARGET_POLIS} tidak ditemukan")
else:
    print(f"\n{SEP}")
    print(f"  SAMPLE 20 BARIS SUSPEND untuk polis {TARGET_POLIS}")
    print(SEP)
    print(f"\nSemua nilai per kolom (non-kosong):\n")
    for col in df.columns:
        vals = sub[col].dropna().astype(str).str.strip()
        vals = vals[vals != ""].unique()[:5]
        if len(vals) > 0:
            print(f"  {col:<35}: {list(vals)}")

# Cek DESC fields khusus
print(f"\n{SEP}")
print(f"  CEK DESC 1-4 untuk polis {TARGET_POLIS}")
print(SEP)

desc_cols = [c for c in df.columns if str(c).upper().startswith("DESC")]
print(f"  Kolom DESC: {desc_cols}")

if not sub.empty and desc_cols:
    for _, row in sub.head(10).iterrows():
        print(f"\n  --- baris {_} ---")
        for dc in desc_cols:
            v = norm(row.get(dc, ""))
            if v:
                print(f"    {dc}: {v}")
        print(f"    RECEIPT DATE : {norm(row.get('RECEIPT DATE', ''))}")
        print(f"    CURR ORI     : {norm(row.get('CURR ORI', ''))}")
        print(f"    AMOUNT ORI   : {norm(row.get('AMOUNT ORI', ''))}")
        print(f"    RECEIPT NO   : {norm(row.get('RECEIPT NO', ''))}")
        print(f"    CREDIT NOTES : {norm(row.get('CREDIT NOTES', ''))}")
        rin = norm(row.get("DETAIL RINCIAN NO", ""))
        if rin:
            print(f"    DETAIL RIN.  : {rin}")

# Cek apakah ada pola BULAN di DESC
print(f"\n{SEP}")
print(f"  ANALISIS DESC — apakah mengandung info bulan/periode?")
print(SEP)

MONTH_RE = re.compile(
    r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|"
    r"JANUARY|FEBRUARY|MARCH|APRIL|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|"
    r"\d{4}[-/]\d{2}|\d{2}[-/]\d{4}|\d{2}/\d{4})\b",
    re.IGNORECASE,
)

if desc_cols and not sub.empty:
    n_with_month = 0
    for _, row in sub.iterrows():
        for dc in desc_cols:
            v = str(row.get(dc, ""))
            if MONTH_RE.search(v):
                n_with_month += 1
                break
    print(f"  Dari 20 sample baris: {n_with_month} mengandung info bulan/periode di DESC")

    # Cek semua baris suspend yang fac code > 1 — apakah DESC punya pola bulan?
    all_desc_concat = ""
    for _, row in sub.iterrows():
        for dc in desc_cols:
            all_desc_concat += " " + str(row.get(dc, ""))

    months_found = set(MONTH_RE.findall(all_desc_concat.upper()))
    print(f"  Bulan/periode yang ditemukan di DESC sample: {months_found}")

# Cek CLSDT_SLIP_NO dan FAC_SLIP apakah ada info tambahan
print(f"\n{SEP}")
print(f"  CEK SLIP INFO untuk polis {TARGET_POLIS}")
print(SEP)

slip_cols = ["CLSDT_SLIP_NO", "FAC_SLIP", "slip_ori", "clean slip 1"]
for col in slip_cols:
    if col in df.columns and not sub.empty:
        vals = sub[col].dropna().astype(str).str.strip().unique()[:5]
        if len(vals) > 0:
            print(f"  {col:<25}: {list(vals)}")

# Kesimpulan: apa field yang BISA membedakan tanpa rule baru?
print(f"\n{SEP}")
print("  ANALISIS: Apakah ada info yang SUDAH ADA di suspend untuk membedakan?")
print(SEP)
print("""
  Yang diperiksa:
  1. DESC 1-4  → apakah berisi info bulan/periode yang bisa dijadikan pembeda?
  2. SLIP      → apakah nomor slip berbeda per bulan?
  3. AMOUNT    → apakah amount bisa membedakan (tiap fac code punya amount berbeda)?
  4. RECEIPT   → apakah nomor receipt mengandung info bulan?
  
  Cek nilai DESC, SLIP, dan RECEIPT di atas untuk menentukan apakah
  ada pembeda yang SUDAH ADA tanpa perlu tambah rule baru.
""")
