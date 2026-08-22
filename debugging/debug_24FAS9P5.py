# -*- coding: utf-8 -*-
"""
Debug (fast): kenapa polis 100030823120000107 tidak match ke fac code 24FAS9P5?
Menggunakan pickle cache agar cepat.
Jalankan: python debug_24FAS9P5.py
"""
import sys, io, re, os
sys.modules['numexpr']  = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

TARGET_POLIS  = "100030823120000107"
TARGET_FAC    = "24FAS9P5"

SUSPEND_FILE  = "data/suspend_clean_aca.xlsx"
OSBAL_FILE    = "data/osbal_clean_aca.xlsx"

def norm(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().upper())

def load_pkl(path):
    """Gunakan cache pkl kalau ada, fallback ke read_excel."""
    cache = path + ".cache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        print(f"    Loading from cache: {cache}")
        data, header = pd.read_pickle(cache)
        return pd.DataFrame(data, columns=header)
    print(f"    Reading Excel (mungkin lambat): {path}")
    return pd.read_excel(path)

SEP = "=" * 70

print(f"\n{SEP}")
print(f"  DEBUG: polis={TARGET_POLIS}  |  target fac={TARGET_FAC}")
print(SEP)

# ── Load ──────────────────────────────────────────────────────────────────────
print("\n[1] Loading data ...")
sus_df = load_pkl(SUSPEND_FILE)
osl_df = load_pkl(OSBAL_FILE)
print(f"    Suspend : {len(sus_df):,} rows x {len(sus_df.columns)} cols")
print(f"    OSBAL   : {len(osl_df):,} rows x {len(osl_df.columns)} cols")

# helper kolom
clean_polis_sus = [c for c in sus_df.columns if str(c).lower().startswith("clean polis")]
clean_slip_sus  = [c for c in sus_df.columns if str(c).lower().startswith("clean slip")]
clean_polis_osl = [c for c in osl_df.columns if str(c).lower().startswith("clean polis")]
clean_slip_osl  = [c for c in osl_df.columns if str(c).lower().startswith("clean slip")]
clsdt_pol_osl   = "CLSDT_POLICY_NO" if "CLSDT_POLICY_NO" in osl_df.columns else None

print(f"\n    Sus  clean polis cols : {clean_polis_sus}")
print(f"    Sus  clean slip  cols : {clean_slip_sus}")
print(f"    OSB  clean polis cols : {clean_polis_osl}")
print(f"    OSB  CLSDT_POLICY_NO  : {'ada' if clsdt_pol_osl else 'tidak ada'}")

# ── [2] Baris OSBAL dengan fac=24FAS9P5 ───────────────────────────────────────
print(f"\n{SEP}")
print(f"[2] Baris OSBAL dengan CCOS_REF_CODE = '{TARGET_FAC}'")
print(SEP)

osl_fac_rows = osl_df[osl_df["CCOS_REF_CODE"].astype(str).str.strip().str.upper() == TARGET_FAC]

if osl_fac_rows.empty:
    print(f"    [!] '{TARGET_FAC}' TIDAK ditemukan di OSBAL!")
else:
    print(f"    Ditemukan {len(osl_fac_rows)} baris:\n")
    for idx, row in osl_fac_rows.iterrows():
        print(f"    --- Baris OSBAL #{idx} ---")
        print(f"       CCOS_REF_CODE   : {norm(row.get('CCOS_REF_CODE'))}")
        print(f"       CCOS_CURR       : {norm(row.get('CCOS_CURR'))}")
        if clsdt_pol_osl:
            print(f"       CLSDT_POLICY_NO : {norm(row.get('CLSDT_POLICY_NO', ''))!r}")
        for cc in clean_polis_osl:
            print(f"       {cc:<25}: {norm(row.get(cc, ''))!r}")
        for cc in clean_slip_osl:
            v = norm(row.get(cc, ""))
            if v:
                print(f"       {cc:<25}: {v!r}")

        # Kolom index OSBAL: clean polis + CLSDT_POLICY_NO
        idx_cols = clean_polis_osl + ([clsdt_pol_osl] if clsdt_pol_osl else [])
        polis_vals_indexed = {norm(row.get(cc, "")) for cc in idx_cols}
        polis_vals_indexed.discard("")
        print(f"\n       → Nilai polis yang masuk index OSBAL : {polis_vals_indexed}")
        print(f"       → TARGET_POLIS exact-match di index?  : {TARGET_POLIS in polis_vals_indexed}")
        if TARGET_POLIS not in polis_vals_indexed:
            sub = [v for v in polis_vals_indexed if TARGET_POLIS in v or v in TARGET_POLIS]
            print(f"       → Sebagai substring (LIKE match)?     : {sub if sub else 'Tidak ada'}")

# ── [3] Baris Suspend dengan polis target ─────────────────────────────────────
print(f"\n{SEP}")
print(f"[3] Baris SUSPEND yang mengandung polis '{TARGET_POLIS}'")
print(SEP)

search_cols = clean_polis_sus + [c for c in ["CLSDT_POLICY_NO", "FAC_POLICY_NO", "polis_ori"]
                                  if c in sus_df.columns]
mask = pd.Series(False, index=sus_df.index)
for col in search_cols:
    mask |= sus_df[col].astype(str).str.upper().str.strip().str.contains(
        re.escape(TARGET_POLIS), na=False, regex=False)

sus_polis_rows = sus_df[mask]
if sus_polis_rows.empty:
    print(f"    [!] Polis '{TARGET_POLIS}' tidak ditemukan di suspend sama sekali!")
else:
    print(f"    Ditemukan {len(sus_polis_rows)} baris suspend:\n")
    for idx, row in sus_polis_rows.iterrows():
        clsdt_p = norm(row.get("CLSDT_POLICY_NO", ""))
        fac_p   = norm(row.get("FAC_POLICY_NO",   ""))
        curr    = norm(row.get("CURR ORI",         ""))
        print(f"    --- Baris Suspend #{idx} ---")
        print(f"       CLSDT_POLICY_NO : {clsdt_p!r}  {'← DIPAKAI utk exact' if clsdt_p else '← KOSONG → pakai clean polis'}")
        print(f"       FAC_POLICY_NO   : {fac_p!r}")
        print(f"       CURR ORI        : {curr!r}")
        for cc in clean_polis_sus:
            print(f"       {cc:<25}: {norm(row.get(cc, ''))!r}")

        if clsdt_p:
            eff = [clsdt_p]
        else:
            eff = [norm(row.get(cc, "")) for cc in clean_polis_sus if norm(row.get(cc, ""))]
        print(f"\n       → Effective polis exact-match values : {eff}")
        print(f"       → TARGET_POLIS ada di effective?     : {TARGET_POLIS in eff}")

# ── [4] Simulasi index OSBAL — siapa saja yang match via polis ────────────────
print(f"\n{SEP}")
print(f"[4] Simulasi: siapa saja di OSBAL yang match polis '{TARGET_POLIS}'?")
print(SEP)

idx_cols_osl = clean_polis_osl + ([clsdt_pol_osl] if clsdt_pol_osl else [])
osl_index = {}
for i, (idx, row) in enumerate(osl_df.iterrows()):
    for cc in idx_cols_osl:
        v = norm(row.get(cc, ""))
        if v:
            osl_index.setdefault(v, []).append({
                "df_idx": idx, "row_i": i,
                "fac": norm(row.get("CCOS_REF_CODE", "")),
                "curr": norm(row.get("CCOS_CURR", "")),
                "col": cc,
            })

if TARGET_POLIS in osl_index:
    hits = osl_index[TARGET_POLIS]
    print(f"    [OK] '{TARGET_POLIS}' ditemukan di index OSBAL → {len(hits)} kandidat:")
    for h in hits:
        tag = " ← TARGET" if h["fac"] == TARGET_FAC else ""
        print(f"       baris {h['df_idx']:>5} | fac={h['fac']:<12} | curr={h['curr']:<5} | via col '{h['col']}'{tag}")
    facs = {h['fac'] for h in hits}
    print(f"\n    Semua fac codes yang match via polis: {facs}")
    print(f"    Target fac '{TARGET_FAC}' ada di sini? : {TARGET_FAC in facs}")
    if len(hits) == 1:
        print(f"\n    [!] Hanya 1 kandidat → currency narrowing TIDAK jalan (butuh >1).")
        print(f"        Langsung dipakai fac: {hits[0]['fac']}")
else:
    print(f"    [!] '{TARGET_POLIS}' TIDAK ada di exact-index OSBAL.")
    print(f"\n    Cek LIKE match (TARGET_POLIS sebagai substring dari nilai clean polis OSBAL):")
    like_hits = []
    for i, (idx, row) in enumerate(osl_df.iterrows()):
        for cc in idx_cols_osl:
            v = norm(row.get(cc, ""))
            if v and TARGET_POLIS in v:
                like_hits.append({"df_idx": idx, "col": cc, "val": v,
                                   "fac": norm(row.get("CCOS_REF_CODE", "")),
                                   "curr": norm(row.get("CCOS_CURR", ""))})
    if like_hits:
        for h in like_hits:
            print(f"       baris {h['df_idx']:>5} | fac={h['fac']:<12} | curr={h['curr']:<5} | col='{h['col']}' | val='{h['val']}'")
    else:
        print(f"       Tidak ada LIKE match untuk '{TARGET_POLIS}' di OSBAL.")

# ── [5] Kenapa 24FAS9P5 tidak masuk index? ───────────────────────────────────
print(f"\n{SEP}")
print(f"[5] Kenapa '{TARGET_FAC}' tidak masuk index polis OSBAL? (excluded check)")
print(SEP)

_EXCLUDED = ["HUTANG PIUTANG", "DATA SUSPENSE"]

if not osl_fac_rows.empty:
    for idx, row in osl_fac_rows.iterrows():
        polis_vals = {norm(row.get(cc, "")) for cc in idx_cols_osl}
        slip_vals  = {norm(row.get(cc, "")) for cc in clean_slip_osl + (["CLSDT_SLIP_NO"] if "CLSDT_SLIP_NO" in osl_df.columns else [])}
        all_vals   = polis_vals | slip_vals | {norm(row.get("polis_ori", "")), norm(row.get("slip_ori", ""))}
        all_vals.discard("")

        is_excluded = any(m in v for v in all_vals for m in _EXCLUDED)
        print(f"    Baris OSBAL #{idx} | fac={norm(row.get('CCOS_REF_CODE'))}")
        print(f"       Semua nilai polis/slip   : {all_vals}")
        print(f"       Kena _is_excluded_ref_row? : {is_excluded}")
        if TARGET_POLIS in polis_vals:
            print(f"       TARGET_POLIS di index    : YA ← baris ini HARUSNYA match!")
        else:
            print(f"       TARGET_POLIS di index    : TIDAK ← inilah kenapa tidak match")

print(f"\n{SEP}")
print("  SELESAI")
print(SEP)
