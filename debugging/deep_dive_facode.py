# -*- coding: utf-8 -*-
"""
deep_dive_facode.py — Investigasi mendalam untuk top polis yang paling banyak
menyebabkan fac code > 1. Lihat PERSIS mengapa currency & periode narrowing
tidak bisa menyelesaikannya.

Jalankan: python deep_dive_facode.py
"""
import sys, io, re, os, time
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

OSBAL_FILE   = os.path.join("data", "osbal_clean_aca.xlsx")
SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")
OUTPUT_FILE  = os.path.join("data", "final_output_v1.xlsx")

OSBAL_FACODE_COL = "CCOS_REF_CODE"
OSBAL_CURR_COL   = "CCOS_CURR"
OSBAL_DATE_COL   = "FAC_COM_DATE"
OSBAL_END_COL    = "FAC_EXP_DATE"   # mungkin ada, mungkin tidak
SUSPEND_CURR_COL = "CURR ORI"
SUSPEND_DATE_COL = "RECEIPT DATE"

SEP  = "=" * 70
SEP2 = "-" * 70

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
    print(f"  {label}: excel ...", flush=True)
    return pd.read_excel(path)

print(f"\n{SEP}")
print("  DEEP DIVE: Kenapa Fac Code > 1 tidak bisa diselesaikan?")
print(SEP)

# ── LOAD ──────────────────────────────────────────────────────────────────────
print("\n[0] Loading data ...")
df_osbal   = load_pkl(OSBAL_FILE,   "OSBAL")
df_suspend = load_pkl(SUSPEND_FILE, "SUSPEND")
df_output  = None
if os.path.exists(OUTPUT_FILE):
    print("  OUTPUT: excel ...", flush=True)
    df_output = pd.read_excel(OUTPUT_FILE)

polis_osbal   = [c for c in df_osbal.columns   if str(c).lower().startswith("clean polis")]
if "CLSDT_POLICY_NO" in df_osbal.columns:
    polis_osbal = ["CLSDT_POLICY_NO"] + polis_osbal
slip_osbal    = [c for c in df_osbal.columns   if str(c).lower().startswith("clean slip")]
polis_suspend = [c for c in df_suspend.columns if str(c).lower().startswith("clean polis")]
slip_suspend  = [c for c in df_suspend.columns if str(c).lower().startswith("clean slip")]

# Top polis dari investigasi sebelumnya
TOP_POLIS = [
    "131030824100000013",  # 2,391 baris fac>1
    "131030823110000013",  # 2,015 baris fac>1
    "100030825010000037",  # 1,359 baris fac>1
    "161030825010000019",  # 507 baris
    "100030825120000155",  # 476 baris
]

# ── BUILD OSBAL INDEX ─────────────────────────────────────────────────────────
print("\n[1] Building OSBAL polis index ...", flush=True)
osbal_polis_idx: dict = {}
for i, (_, row) in enumerate(df_osbal.iterrows()):
    fac  = norm(row.get(OSBAL_FACODE_COL, ""))
    curr = norm(row.get(OSBAL_CURR_COL, ""))
    if not fac:
        continue
    for col in polis_osbal:
        val = norm(row.get(col, ""))
        if val and len(val) >= 5:
            osbal_polis_idx.setdefault(val, []).append({
                "row_i": i,
                "fac":   fac,
                "curr":  curr,
                "com_date": row.get(OSBAL_DATE_COL, None),
                "exp_date": row.get(OSBAL_END_COL, None) if OSBAL_END_COL in df_osbal.columns else None,
                "col":  col,
            })

print(f"  Index siap: {len(osbal_polis_idx):,} unique polis values")

# ── ANALISIS PER POLIS ────────────────────────────────────────────────────────
for target_polis in TOP_POLIS:
    print(f"\n{SEP}")
    print(f"  POLIS: {target_polis}")
    print(SEP)

    osbal_hits = osbal_polis_idx.get(target_polis, [])
    if not osbal_hits:
        print(f"  [!] Tidak ditemukan di OSBAL index")
        continue

    fac_codes = sorted({h["fac"] for h in osbal_hits})
    currencies = sorted({h["curr"] for h in osbal_hits if h["curr"]})

    print(f"  Di OSBAL → {len(osbal_hits)} baris, {len(fac_codes)} FAC CODE unik:")
    print(f"  FAC codes : {fac_codes}")
    print(f"  Currencies: {currencies}")
    print()

    # Detail per fac code
    fac_detail: dict = {}
    for h in osbal_hits:
        fac_detail.setdefault(h["fac"], []).append(h)

    print(f"  {'FAC CODE':<14} {'CURR':<8} {'FAC_COM_DATE':<15} {'FAC_EXP_DATE':<15}")
    print(f"  {'-'*14} {'-'*8} {'-'*15} {'-'*15}")
    for fac, rows in sorted(fac_detail.items()):
        for row in rows[:3]:  # max 3 baris per fac code
            com = str(row["com_date"])[:10] if row["com_date"] and str(row["com_date"]) != "nan" else "—"
            exp = str(row["exp_date"])[:10] if row["exp_date"] and str(row["exp_date"]) != "nan" else "—"
            print(f"  {fac:<14} {row['curr']:<8} {com:<15} {exp:<15}")

    # Cek apakah currency bisa memisahkan
    curr_to_facs = {}
    for h in osbal_hits:
        curr_to_facs.setdefault(h["curr"], set()).add(h["fac"])

    can_resolve_currency = all(len(v) == 1 for v in curr_to_facs.values()) and len(curr_to_facs) > 1
    print(f"\n  [A] Apakah CURRENCY bisa membedakan?")
    for curr, facs in sorted(curr_to_facs.items()):
        print(f"      {curr or '(kosong)':<10}: {sorted(facs)}")
    if can_resolve_currency:
        print(f"  → ✅ BISA di-resolve jika currency suspend diketahui & cocok")
    else:
        print(f"  → ❌ Tidak bisa hanya dari currency (semua fac code di currency yang sama)")

    # Cek apakah periode bisa memisahkan
    print(f"\n  [B] Apakah PERIODE (FAC_COM_DATE) bisa membedakan?")
    dates_per_fac = {}
    for fac, rows in fac_detail.items():
        dates = []
        for r in rows:
            if r["com_date"] and str(r["com_date"]) != "nan":
                try:
                    dates.append(pd.to_datetime(r["com_date"]))
                except:
                    pass
        dates_per_fac[fac] = dates

    all_date_ranges = [(fac, min(d) if d else None, max(d) if d else None)
                       for fac, d in dates_per_fac.items()]
    for fac, mn, mx in sorted(all_date_ranges):
        mn_s = str(mn)[:10] if mn else "—"
        mx_s = str(mx)[:10] if mx else "—"
        print(f"      {fac:<14}: {mn_s} ~ {mx_s}")

    # Cek overlap periode antar fac
    periods = [(fac, mn, mx) for fac, mn, mx in all_date_ranges if mn is not None]
    if len(periods) > 1:
        overlaps = False
        for i in range(len(periods)):
            for j in range(i+1, len(periods)):
                f1, mn1, mx1 = periods[i]
                f2, mn2, mx2 = periods[j]
                # overlap: tidak overlap jika mx1 < mn2 atau mx2 < mn1
                if mx1 and mn2 and mx2 and mn1:
                    if not (mx1 < mn2 or mx2 < mn1):
                        overlaps = True
                        print(f"      ⚠ {f1} & {f2} period OVERLAP")
        if not overlaps:
            print(f"  → ✅ BISA di-resolve berdasarkan periode (tidak overlap)")
        else:
            print(f"  → ❌ Ada overlap periode — tidak bisa hanya dari tanggal")
    else:
        print(f"  → [?] Hanya 1 fac code punya tanggal valid")

    # Cek suspend yang match ke polis ini
    print(f"\n  [C] Suspend dengan polis '{target_polis}':")
    sus_mask = pd.Series(False, index=df_suspend.index)
    for col in polis_suspend + ["FAC_POLICY_NO", "CLSDT_POLICY_NO", "polis_ori"]:
        if col in df_suspend.columns:
            sus_mask |= df_suspend[col].astype(str).str.upper().str.strip() == target_polis
    sus_rows = df_suspend[sus_mask]
    print(f"      Total baris suspend: {len(sus_rows)}")
    if not sus_rows.empty:
        # Distribusi currency suspend
        if SUSPEND_CURR_COL in sus_rows.columns:
            curr_dist = sus_rows[SUSPEND_CURR_COL].value_counts()
            print(f"      Currency suspend: {curr_dist.to_dict()}")
        # Distribusi tanggal
        if SUSPEND_DATE_COL in sus_rows.columns:
            dates = sus_rows[SUSPEND_DATE_COL].dropna()
            if not dates.empty:
                try:
                    dates = pd.to_datetime(dates, errors='coerce').dropna()
                    print(f"      RECEIPT DATE range: {dates.min().date()} ~ {dates.max().date()}")
                except:
                    pass
        # Cek berapa yang bisa di-resolve oleh currency match
        if SUSPEND_CURR_COL in sus_rows.columns:
            n_resolved_curr = 0
            for _, srow in sus_rows.iterrows():
                sus_curr = norm(srow.get(SUSPEND_CURR_COL, ""))
                matching_curr_facs = {h["fac"] for h in osbal_hits
                                      if norm(h["curr"]) == sus_curr and sus_curr}
                if len(matching_curr_facs) == 1:
                    n_resolved_curr += 1
            print(f"      Bisa di-resolve oleh currency narrowing: {n_resolved_curr} / {len(sus_rows)}")

    # Cek output: apa label yang diterima baris ini?
    if df_output is not None and "POLIS_CLN" in df_output.columns:
        out_mask = df_output["POLIS_CLN"].astype(str).str.upper().str.strip() == target_polis
        out_rows = df_output[out_mask]
        if not out_rows.empty and "Mark Admin Fac Code" in out_rows.columns:
            marks = out_rows["Mark Admin Fac Code"].value_counts()
            print(f"\n  [D] Di output: {len(out_rows)} baris")
            for mark, cnt in marks.items():
                print(f"      {str(mark):<30}: {cnt}")

# ── RANGKUMAN STRATEGI ────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  RANGKUMAN: Strategi untuk mengurangi fac code > 1")
print(SEP)
print("""
  Dari analisis di atas, kemungkinan penyebab narrowing TIDAK berhasil:

  [1] CURRENCY SAMA — Jika polis muncul di 2 fac code dengan currency yang SAMA
      (misal: IDR semua), currency narrowing tidak bisa membedakan.
      → Butuh pembeda lain (nomor dokumen, insured, periode)

  [2] PERIODE OVERLAP — Jika FAC_COM_DATE ke-2 fac code overlap atau sama,
      periode narrowing tidak bisa membedakan.
      → Butuh FAC_EXP_DATE untuk tahu akhir periode

  [3] DATA GENUINELY AMBIGU — Satu polis memang untuk banyak risiko (1 cedant
      punya 2 kontrak fac yang sama-sama aktif di periode yang sama)
      → Tidak bisa diselesaikan tanpa informasi tambahan dari sumber data

  SARAN TINDAK LANJUT:
  1. Cek kolom FAC_EXP_DATE di OSBAL — apakah ada? Jika ya, bisa dipakai
     untuk narrowing lebih ketat (RECEIPT DATE dalam range COM~EXP)
  2. Cek CCOS_DOC_NO di OSBAL — apakah suspend punya referensi ke doc number?
  3. Koordinasi dengan tim data: polis yang sama di 2 fac code aktif bersamaan
     — apa yang membedakan keduanya secara bisnis?
""")
