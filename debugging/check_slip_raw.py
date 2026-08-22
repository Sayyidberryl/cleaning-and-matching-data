# -*- coding: utf-8 -*-
"""
check_slip_raw.py — Cek apakah slip dari suspend ADA di data asli OSBAL (osbal.xlsx)
Ambil sample slip yang 'POLIS ONLY' dan cari di semua kolom OSBAL asli.

Jalankan: python check_slip_raw.py
"""
import sys, io, re, os
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

OSBAL_RAW_FILE   = os.path.join("data", "osbal.xlsx")
OSBAL_CLEAN_FILE = os.path.join("data", "osbal_clean_aca.xlsx")
SUSPEND_FILE     = os.path.join("data", "suspend_clean_aca.xlsx")

SEP  = "=" * 70
SEP2 = "-" * 60

def norm(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().upper())

def load_pkl(path, label=""):
    cache = path + ".cache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        print(f"  {label}: cache ...", flush=True)
        data, header = pd.read_pickle(cache)
        return pd.DataFrame(data, columns=header)
    print(f"  {label}: excel (mungkin lama) ...", flush=True)
    return pd.read_excel(path)

print(f"\n{SEP}")
print("  CEK SLIP: Apakah slip suspend ada di data ASLI OSBAL?")
print(SEP)

# Sample slip dari kategori BOTH_AMBIGUOUS_NO_SLIP (POLIS ONLY)
# Ini slip yang tidak ketemu di clean OSBAL
SAMPLE_SLIPS = [
    "73103072407003611",
    "73103072406000183",
    "73103072411001785",
    "73103072410001554",
    "73103072407002491",
    "73103072405003675",
    "73103072407001051",
    "73103072409001542",
]
SAMPLE_POLIS = "131030824100000013"  # polis yang associated

print("\n[0] Loading OSBAL cleaned ...")
df_clean = load_pkl(OSBAL_CLEAN_FILE, "OSBAL clean")
print(f"  Cols: {list(df_clean.columns)}")

# Cek semua kolom slip di OSBAL clean
slip_cols_clean = [c for c in df_clean.columns if "slip" in str(c).lower()]
print(f"\n  Kolom slip di OSBAL clean: {slip_cols_clean}")

print(f"\n[1] Cek sample slips di OSBAL CLEAN ...")
for slip in SAMPLE_SLIPS:
    found_in = []
    for col in slip_cols_clean:
        hits = df_clean[df_clean[col].astype(str).str.upper().str.strip() == slip]
        if not hits.empty:
            facs = hits["CCOS_REF_CODE"].dropna().unique()[:3].tolist()
            found_in.append(f"{col}→{len(hits)} baris (fac: {facs})")
    if found_in:
        print(f"  ✅ {slip}: DITEMUKAN — {found_in}")
    else:
        print(f"  ❌ {slip}: TIDAK ditemukan di clean slip columns")

print(f"\n[2] Loading OSBAL RAW (asli) untuk verifikasi ...")
df_raw = pd.read_excel(OSBAL_RAW_FILE)
print(f"  Total rows: {len(df_raw):,}")
print(f"  Total cols: {len(df_raw.columns)}")
print(f"\n  SEMUA kolom di OSBAL asli:")
for c in df_raw.columns:
    print(f"    {c}")

# Cek kolom slip di raw
slip_cols_raw = [c for c in df_raw.columns if "slip" in str(c).lower()]
print(f"\n  Kolom SLIP di OSBAL asli: {slip_cols_raw}")

print(f"\n[3] Cek sample slips di OSBAL RAW (data asli) ...")
for slip in SAMPLE_SLIPS:
    found_in = []
    for col in df_raw.columns:  # cek SEMUA kolom, bukan hanya slip
        try:
            hits = df_raw[df_raw[col].astype(str).str.upper().str.strip() == slip]
            if not hits.empty:
                found_in.append(f"{col}({len(hits)} baris)")
        except:
            pass
    if found_in:
        print(f"  ✅ {slip}: DITEMUKAN di → {found_in}")
    else:
        print(f"  ❌ {slip}: TIDAK ditemukan di MANAPUN di OSBAL asli")

# Cek satu polis secara mendalam di OSBAL asli
print(f"\n[4] Deep-dive polis {SAMPLE_POLIS} di OSBAL asli ...")
polis_cols_raw = [c for c in df_raw.columns if "poli" in str(c).lower() or "policy" in str(c).lower()]
print(f"  Kolom polis raw: {polis_cols_raw}")

polis_hits = pd.Series(False, index=df_raw.index)
for col in polis_cols_raw:
    polis_hits |= df_raw[col].astype(str).str.upper().str.strip().str.contains(SAMPLE_POLIS, na=False)

sub = df_raw[polis_hits]
print(f"  Baris dengan polis {SAMPLE_POLIS}: {len(sub)}")

if not sub.empty:
    print(f"\n  Kolom dan contoh nilai (dari 5 baris pertama):")
    for col in df_raw.columns:
        vals = sub[col].dropna().astype(str).str.strip().unique()[:3]
        vals = [v for v in vals if v and v.lower() not in ("nan", "")]
        if vals:
            print(f"    {col:<35}: {vals}")

# Cek apakah OSBAL punya nomor sertifikat/detail per risiko
print(f"\n[5] Cek struktur data polis di OSBAL asli (10 sample baris) ...")
if not sub.empty:
    for col in slip_cols_raw + polis_cols_raw:
        if col in sub.columns:
            vals = sub[col].dropna().astype(str).str.strip().unique()[:10]
            vals = [v for v in vals if v and v.lower() != "nan"]
            print(f"  {col:<40}: {vals}")

# Bandingkan: slip di suspend vs slip di OSBAL untuk polis yang sama
print(f"\n[6] Perbandingan slip suspend vs OSBAL untuk polis {SAMPLE_POLIS} ...")
df_sus = load_pkl(SUSPEND_FILE, "SUSPEND")
polis_sus_mask = pd.Series(False, index=df_sus.index)
for col in ["clean polis 1", "polis_ori"]:
    if col in df_sus.columns:
        polis_sus_mask |= df_sus[col].astype(str).str.upper().str.strip() == SAMPLE_POLIS
sub_sus = df_sus[polis_sus_mask]

print(f"  Baris suspend dengan polis {SAMPLE_POLIS}: {len(sub_sus)}")
if not sub_sus.empty:
    sus_slips = set()
    for col in ["clean slip 1", "slip_ori"]:
        if col in sub_sus.columns:
            vals = sub_sus[col].dropna().astype(str).str.strip().unique()
            sus_slips.update(v for v in vals if v and v.lower() != "nan")
    print(f"  Slip di suspend (sample 10): {sorted(list(sus_slips))[:10]}")

if not sub.empty:
    osbal_slips = set()
    for col in slip_cols_raw:
        vals = sub[col].dropna().astype(str).str.strip().unique()
        osbal_slips.update(v for v in vals if v and v.lower() != "nan")
    print(f"  Slip di OSBAL asli          : {sorted(list(osbal_slips))[:10]}")

    # Overlap
    if sus_slips and osbal_slips:
        overlap = sus_slips & osbal_slips
        print(f"\n  IRISAN (slip yang ada di keduanya): {sorted(list(overlap))[:10]}")
        print(f"  Hanya di suspend  : {len(sus_slips - osbal_slips)}")
        print(f"  Hanya di OSBAL    : {len(osbal_slips - sus_slips)}")
        print(f"  Ada di keduanya   : {len(overlap)}")
