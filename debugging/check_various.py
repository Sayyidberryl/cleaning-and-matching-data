# -*- coding: utf-8 -*-
"""
check_various.py — Cek apakah VARIOUS benar-benar dipakai untuk matching.
Jalankan: python check_various.py
"""
import sys, io, re, os, time
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

SEP = "=" * 70

FACUL_FILE   = os.path.join("data", "facul_clean_aca.xlsx")
OSBAL_FILE   = os.path.join("data", "osbal_clean_aca.xlsx")
SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")

def norm(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().upper())

def load_pkl(path, label=""):
    cache = path + ".cache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        t = time.perf_counter()
        print(f"  {label}: loading cache ...", flush=True)
        data, header = pd.read_pickle(cache)
        df = pd.DataFrame(data, columns=header)
        print(f"  → {len(df):,} rows ({time.perf_counter()-t:.2f}s)")
        return df
    t = time.perf_counter()
    print(f"  {label}: reading Excel ...", flush=True)
    df = pd.read_excel(path)
    print(f"  → {len(df):,} rows ({time.perf_counter()-t:.1f}s)")
    return df

print(f"\n{SEP}")
print("  CEK APAKAH 'VARIOUS' DIPAKAI UNTUK MATCHING")
print(SEP)

# Target kata-kata generik
GENERIC_VALS = ["VARIOUS", "AS PER LIST", "AS PER LIST ATTACHED", "TBA"]

# ── LOAD ──────────────────────────────────────────────────────────────────────
print("\n[1] Loading data ...")
df_facul   = load_pkl(FACUL_FILE,   "FACUL")
df_osbal   = load_pkl(OSBAL_FILE,   "OSBAL")
df_suspend = load_pkl(SUSPEND_FILE, "SUSPEND")

polis_facul   = [c for c in df_facul.columns   if str(c).lower().startswith("clean polis")]
polis_osbal   = [c for c in df_osbal.columns   if str(c).lower().startswith("clean polis")]
polis_suspend = [c for c in df_suspend.columns if str(c).lower().startswith("clean polis")]

print(f"\n  FACUL   clean polis cols: {polis_facul}")
print(f"  OSBAL   clean polis cols: {polis_osbal}")
print(f"  SUSPEND clean polis cols: {polis_suspend}")

# ── [2] CEK FACUL — berapa baris punya VARIOUS di clean polis? ─────────────
print(f"\n{SEP}")
print("[2] FACUL — berapa baris punya nilai generik di clean polis?")
print(SEP)

for generic in GENERIC_VALS:
    mask = pd.Series(False, index=df_facul.index)
    for col in polis_facul:
        mask |= df_facul[col].astype(str).str.upper().str.strip() == generic
    cnt = mask.sum()
    if cnt > 0:
        print(f"  '{generic}': {cnt:,} baris di FACUL (akan masuk index matching!)")
        # Tampilkan beberapa contoh FAC_CODE yang kena
        sample_fac = df_facul[mask]["FAC_CODE"].dropna().unique()[:10]
        print(f"    → FAC_CODE sample: {list(sample_fac)}")

# ── [3] CEK OSBAL — berapa baris punya VARIOUS di clean polis? ─────────────
print(f"\n{SEP}")
print("[3] OSBAL — berapa baris punya nilai generik di clean polis?")
print(SEP)

osbal_polis_plus = polis_osbal + (["CLSDT_POLICY_NO"] if "CLSDT_POLICY_NO" in df_osbal.columns else [])

for generic in GENERIC_VALS:
    mask = pd.Series(False, index=df_osbal.index)
    for col in osbal_polis_plus:
        mask |= df_osbal[col].astype(str).str.upper().str.strip() == generic
    cnt = mask.sum()
    if cnt > 0:
        sample_fac = df_osbal[mask]["CCOS_REF_CODE"].dropna().unique()[:10]
        print(f"  '{generic}': {cnt:,} baris di OSBAL")
        print(f"    → CCOS_REF_CODE sample: {list(sample_fac)}")

# ── [4] CEK SUSPEND — berapa baris punya VARIOUS di clean polis? ───────────
print(f"\n{SEP}")
print("[4] SUSPEND — berapa baris punya nilai generik di clean polis?")
print(SEP)

sus_polis_all = polis_suspend + ["FAC_POLICY_NO", "CLSDT_POLICY_NO", "polis_ori"]
sus_polis_all = [c for c in sus_polis_all if c in df_suspend.columns]

any_found = False
for generic in GENERIC_VALS:
    mask = pd.Series(False, index=df_suspend.index)
    for col in sus_polis_all:
        mask |= df_suspend[col].astype(str).str.upper().str.strip() == generic
    cnt = mask.sum()
    if cnt > 0:
        any_found = True
        print(f"  '{generic}': {cnt:,} baris di SUSPEND clean polis/ori")
        sample = df_suspend[mask][sus_polis_all[:3]].head(5)
        print(f"    Contoh:\n{sample.to_string()}")

if not any_found:
    print("  TIDAK ADA baris suspend yang clean polis-nya berisi VARIOUS/TBA/dll.")
    print("  → VARIOUS tidak akan menyebabkan false match dari sisi suspend!")

# ── [5] CEK: VARIOUS di polis_ori suspend sebelum cleaning ─────────────────
print(f"\n{SEP}")
print("[5] SUSPEND polis_ori — berapa yang awalnya VARIOUS sebelum cleaned?")
print(SEP)

if "polis_ori" in df_suspend.columns:
    for generic in GENERIC_VALS:
        mask = df_suspend["polis_ori"].astype(str).str.upper().str.strip() == generic
        cnt = mask.sum()
        if cnt > 0:
            print(f"  polis_ori = '{generic}': {cnt:,} baris")
            # Cek apa clean polis 1-nya setelah cleaning
            sample = df_suspend[mask][["polis_ori"] + polis_suspend[:2]].head(5)
            print(f"    Contoh:\n{sample.to_string()}")
    
    # Cek juga dengan contains
    mask_var = df_suspend["polis_ori"].astype(str).str.upper().str.contains("VARIOUS", na=False)
    print(f"\n  polis_ori MENGANDUNG kata 'VARIOUS': {mask_var.sum():,} baris")

# ── [6] CEK: Bagaimana VARIOUS di FACUL berbeda dengan VARIOUS di OSBAL ────
print(f"\n{SEP}")
print("[6] ANALISIS: apakah VARIOUS di FACUL akan ter-match oleh suspend?")
print(SEP)

# Cek berapa suspend yang punya FAC_POLICY_NO atau CLSDT yang akan clean jadi VARIOUS
if "FAC_POLICY_NO" in df_suspend.columns:
    mask = df_suspend["FAC_POLICY_NO"].astype(str).str.upper().str.strip().str.contains("VARIOUS", na=False)
    cnt = mask.sum()
    print(f"  Suspend dengan FAC_POLICY_NO mengandung VARIOUS: {cnt:,} baris")

# Cek final: berapa baris suspend yang akan match ke VARIOUS di index FACUL
# Ini terjadi jika clean_polis di suspend = "VARIOUS"
various_in_suspend_clean = False
for col in polis_suspend:
    cnt = (df_suspend[col].astype(str).str.upper().str.strip() == "VARIOUS").sum()
    if cnt > 0:
        various_in_suspend_clean = True
        print(f"  suspend {col} = 'VARIOUS': {cnt:,} baris → AKAN MATCH ke semua FACUL VARIOUS!")

if not various_in_suspend_clean:
    print("  ✅ AMAN: Tidak ada suspend clean polis yang berisi 'VARIOUS' persis.")
    print("     Jadi VARIOUS di FACUL tidak akan langsung menjadi kandidat match.")
    print("     TAPI: FACUL 'VARIOUS' masuk ke index, dan ini PEMBOROSAN memori saja.")

# ── [7] Bagaimana FAC_POLICY_NO suspend yang VARIOUS di-clean? ─────────────
print(f"\n{SEP}")
print("[7] Trace: suspend dengan FAC_POLICY_NO mengandung VARIOUS → clean polis apa?")
print(SEP)

if "FAC_POLICY_NO" in df_suspend.columns:
    mask_var = df_suspend["FAC_POLICY_NO"].astype(str).str.upper().str.contains("VARIOUS", na=False)
    sample_var = df_suspend[mask_var][["FAC_POLICY_NO"] + polis_suspend[:3]].head(10)
    if not sample_var.empty:
        print(sample_var.to_string())
    else:
        print("  Tidak ada.")

print(f"\n{SEP}")
print("  KESIMPULAN")
print(SEP)
print("""
  INGAT: 'VARIOUS' di FACUL adalah nilai di kolom FAC_POLICY_NO dari FACUL itu sendiri.
  Ini muncul karena dalam data FACUL ada polis yang isinya "VARIOUS" (satu fac code
  menanggung banyak risiko tanpa nomor polis spesifik).
  
  Pertanyaan kritis: Apakah suspend juga punya clean_polis = "VARIOUS"?
  → Jika YA: suspend akan match ke semua 2,609 fac code FACUL! (masalah besar)
  → Jika TIDAK: VARIOUS di FACUL hanya memboroskan memori tapi tidak menyebabkan false match
  
  Lihat hasil di atas untuk jawaban aktual dari data.
""")
