# -*- coding: utf-8 -*-
"""
Debug script: trace mengapa nilai tertentu tidak ter-match.
Jalankan: python debug_trace.py
"""
import sys
import io
sys.modules['numexpr'] = None
sys.modules['bottleneck'] = None

# Force UTF-8 output agar tidak error di Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import re

TARGET = "100010324120003582"   # nilai yang ingin ditelusuri

SUSPEND_FILE = "data/suspend_clean_aca.xlsx"
OSBAL_FILE   = "data/osbal_clean_aca.xlsx"

def _normalize(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().upper()
    return re.sub(r"\s+", " ", text) if "  " in text else text

print(f"\n{'='*60}")
print(f"  DEBUG TRACE: {TARGET}")
print(f"{'='*60}")

# Load
print("\n[1] Loading data ...")
sus_df = pd.read_excel(SUSPEND_FILE)
osl_df = pd.read_excel(OSBAL_FILE)
print(f"    Suspend : {len(sus_df):,} rows x {len(sus_df.columns)} cols")
print(f"    OSBAL   : {len(osl_df):,} rows x {len(osl_df.columns)} cols")

# ─── Cari di SUSPEND ─────────────────────────────────────────────────────────
print(f"\n[2] Mencari '{TARGET}' di SUSPEND ...")
sus_hits = {}
for col in sus_df.columns:
    mask = sus_df[col].astype(str).str.upper().str.strip().str.contains(
        re.escape(TARGET), na=False, regex=False
    )
    if mask.any():
        rows = sus_df[mask].index.tolist()
        sus_hits[col] = rows

if not sus_hits:
    print(f"    [!] Nilai '{TARGET}' TIDAK ditemukan di suspend sama sekali!")
else:
    for col, rows in sus_hits.items():
        print(f"    [OK] suspend['{col}'] → baris {rows}")
        for ri in rows[:3]:
            row = sus_df.iloc[ri]
            print(f"       CLSDT_POLICY_NO : {_normalize(row.get('CLSDT_POLICY_NO', 'N/A'))}")
            print(f"       CLSDT_SLIP_NO   : {_normalize(row.get('CLSDT_SLIP_NO',   'N/A'))}")
            print(f"       FAC_POLICY_NO   : {_normalize(row.get('FAC_POLICY_NO',   'N/A'))}")
            print(f"       FAC_SLIP        : {_normalize(row.get('FAC_SLIP',         'N/A'))}")
            # Tampilkan semua clean cols
            clean_cols = [c for c in sus_df.columns if str(c).lower().startswith("clean polis")
                          or str(c).lower().startswith("clean slip")]
            for cc in clean_cols:
                v = _normalize(row.get(cc, ""))
                if v:
                    print(f"       {cc:<25}: {v}")

# ─── Cari di OSBAL ────────────────────────────────────────────────────────────
print(f"\n[3] Mencari '{TARGET}' di OSBAL ...")
osl_hits = {}
for col in osl_df.columns:
    mask = osl_df[col].astype(str).str.upper().str.strip().str.contains(
        re.escape(TARGET), na=False, regex=False
    )
    if mask.any():
        rows = osl_df[mask].index.tolist()
        osl_hits[col] = rows

if not osl_hits:
    print(f"    [!] Nilai '{TARGET}' TIDAK ditemukan di OSBAL!")
else:
    for col, rows in osl_hits.items():
        print(f"    [OK] osbal['{col}'] → baris {rows}")
        for ri in rows[:3]:
            row = osl_df.iloc[ri]
            # Tampilkan semua clean cols di osbal
            clean_cols = [c for c in osl_df.columns if str(c).lower().startswith("clean polis")
                          or str(c).lower().startswith("clean slip")]
            for cc in clean_cols:
                v = _normalize(row.get(cc, ""))
                if v:
                    print(f"       {cc:<25}: {v}")
            print(f"       CCOS_REF_CODE   : {_normalize(row.get('CCOS_REF_CODE', 'N/A'))}")
            print(f"       CCOS_CURR       : {_normalize(row.get('CCOS_CURR', 'N/A'))}")

# ─── Analisis mismatch ────────────────────────────────────────────────────────
print(f"\n[4] Analisis ...")
if sus_hits and osl_hits:
    sus_cols_with_target = list(sus_hits.keys())
    osl_cols_with_target = list(osl_hits.keys())
    print(f"    Nilai ada di suspend   : {sus_cols_with_target}")
    print(f"    Nilai ada di OSBAL     : {osl_cols_with_target}")

    # Cek apakah nilai di suspend ada di kolom yang dipakai untuk matching
    clsdt_cols    = ["CLSDT_POLICY_NO", "CLSDT_SLIP_NO"]
    fac_cols      = ["FAC_POLICY_NO", "FAC_SLIP"]
    clean_polis   = [c for c in sus_df.columns if str(c).lower().startswith("clean polis")]
    clean_slip    = [c for c in sus_df.columns if str(c).lower().startswith("clean slip")]

    used_for_exact = clsdt_cols + clean_polis + clean_slip
    used_for_like  = used_for_exact + fac_cols

    in_exact = [c for c in sus_cols_with_target if c in used_for_exact]
    in_like  = [c for c in sus_cols_with_target if c in used_for_like]

    print(f"\n    Kolom suspend yang dipakai EXACT matching  : {in_exact if in_exact else '(tidak ada!)'}")
    print(f"    Kolom suspend yang dipakai LIKE matching   : {in_like  if in_like  else '(tidak ada!)'}")

    # Cek apakah nilai di OSBAL ada di kolom clean
    osl_clean_cols = [c for c in osl_df.columns if str(c).lower().startswith("clean polis")
                      or str(c).lower().startswith("clean slip")]
    osl_in_clean   = [c for c in osl_cols_with_target if c in osl_clean_cols]

    print(f"\n    Kolom OSBAL yang mengandung nilai          : {osl_cols_with_target}")
    print(f"    Di antaranya yang clean cols (di-index)    : {osl_in_clean if osl_in_clean else '(tidak ada!)'}")

    if not in_exact and not in_like:
        print("\n    [KESIMPULAN] Nilai ada di suspend tapi di kolom yang TIDAK dipakai matching sama sekali.")
    elif not osl_in_clean:
        print("\n    [KESIMPULAN] Nilai ada di OSBAL tapi di kolom yang TIDAK di-index (bukan clean polis/slip).")
        print(f"    → Kolom OSBAL yang mengandung nilai: {osl_cols_with_target}")
    else:
        print("\n    [INFO] Nilai ada di kedua sisi kolom yang benar — cek normalisasi atau token matching.")

        # Cek exact normalization
        sus_row = sus_df[sus_df[sus_cols_with_target[0]].astype(str).str.upper().str.strip()
                         .str.contains(TARGET, na=False, regex=False)].iloc[0]
        for sc in in_exact:
            sv = _normalize(sus_row.get(sc, ""))
            print(f"\n    Suspend nilai di '{sc}': '{sv}'")
            for oc in osl_clean_cols:
                osl_match = osl_df[osl_df[oc].astype(str).str.upper().str.strip()
                                   .str.contains(TARGET, na=False, regex=False)]
                if not osl_match.empty:
                    ov = _normalize(osl_match.iloc[0].get(oc, ""))
                    print(f"    OSBAL nilai di '{oc}': '{ov}'")
                    print(f"    Match exact? {sv == ov} | TARGET in ov? {TARGET in ov} | ov in sv? {ov in sv}")

print("\n" + "="*60)
