# -*- coding: utf-8 -*-
"""
investigate_facode.py — Investigasi mendalam:
  1. Kenapa fac code lebih dari 1 banyak? Apa penyebab utamanya?
  2. Apakah ada ketidakefisienan kode?

Menggunakan pickle cache agar loading cepat.
Jalankan: python investigate_facode.py
"""
import sys, io, re, os, time, collections
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np

SEP  = "=" * 70
SEP2 = "-" * 70

OSBAL_FILE   = os.path.join("data", "osbal_clean_aca.xlsx")
FACUL_FILE   = os.path.join("data", "facul_clean_aca.xlsx")
SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")
OUTPUT_V1    = os.path.join("data", "final_output_v1.xlsx")
OUTPUT_V2    = os.path.join("data", "final_output_v2.xlsx")
OUTPUT_FINAL = os.path.join("data", "final_output.xlsx")

OSBAL_FACODE_COL = "CCOS_REF_CODE"
FACUL_FACODE_COL = "FAC_CODE"

# ── Helper ────────────────────────────────────────────────────────────────────

def norm(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().upper())

def load_pkl(path, label=""):
    cache = path + ".cache.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        t = time.perf_counter()
        print(f"  {label}: loading from cache ...", flush=True)
        data, header = pd.read_pickle(cache)
        df = pd.DataFrame(data, columns=header)
        print(f"  → {len(df):,} rows, {len(df.columns)} cols ({time.perf_counter()-t:.2f}s)")
        return df
    t = time.perf_counter()
    print(f"  {label}: reading Excel (mungkin lambat) ...", flush=True)
    df = pd.read_excel(path)
    print(f"  → {len(df):,} rows ({time.perf_counter()-t:.1f}s)")
    return df

def load_output(path, label=""):
    if not os.path.exists(path):
        print(f"  [SKIP] {label}: {path} tidak ditemukan.")
        return None
    t = time.perf_counter()
    print(f"  {label}: reading ...", flush=True)
    df = pd.read_excel(path)
    print(f"  → {len(df):,} rows ({time.perf_counter()-t:.1f}s)")
    return df


# =============================================================================
# [A] ANALISIS OUTPUT: fac code lebih dari 1
# =============================================================================

def analyze_facode_gt1(df_out, label=""):
    """Analisis baris dengan 'fac code lebih dari 1' di output."""
    if df_out is None:
        return
    print(f"\n{SEP}")
    print(f"  [A] ANALISIS 'fac code lebih dari 1' — {label}")
    print(SEP)

    if "Mark Admin Fac Code" not in df_out.columns:
        print("  [!] Kolom 'Mark Admin Fac Code' tidak ada di output ini.")
        return

    df_gt1 = df_out[df_out["Mark Admin Fac Code"].astype(str).str.strip() == "facode lebih dari 1"]
    df_single = df_out[df_out["Mark Admin Fac Code"].astype(str).str.strip() != "facode lebih dari 1"]
    pct = len(df_gt1) / len(df_out) * 100 if len(df_out) else 0
    print(f"  Total baris           : {len(df_out):,}")
    print(f"  facode lebih dari 1   : {len(df_gt1):,} ({pct:.1f}%)")
    print(f"  facode single / lain  : {len(df_single):,}")

    # -- A1: Distribusi SKENARIO pada baris fac code > 1
    if "SKENARIO" in df_gt1.columns:
        print(f"\n  [A1] Distribusi SKENARIO pada baris 'fac code > 1':")
        print(SEP2)
        for sce, cnt in df_gt1["SKENARIO"].value_counts().items():
            print(f"    {str(sce):<40}: {cnt:,}")

    # -- A2: Distribusi FLAG_PROD
    if "FLAG_PROD" in df_gt1.columns:
        print(f"\n  [A2] Distribusi FLAG_PROD pada baris 'fac code > 1':")
        print(SEP2)
        for fp, cnt in df_gt1["FLAG_PROD"].value_counts().items():
            print(f"    {str(fp):<40}: {cnt:,}")

    # -- A3: Berapa banyak CCOS_REF_CODE unik per baris?
    if "CCOS_REF_CODE" in df_gt1.columns:
        print(f"\n  [A3] Contoh CCOS_REF_CODE pada baris 'fac code > 1' (10 sample):")
        print(SEP2)
        samples = df_gt1["CCOS_REF_CODE"].dropna().head(10).tolist()
        for s in samples:
            codes = [x.strip() for x in str(s).split(",") if x.strip()]
            print(f"    {len(codes)} codes: {codes[:8]}")

    # -- A4: Apakah ada baris fac code > 1 yang sebenarnya single setelah split?
    if "CCOS_REF_CODE" in df_gt1.columns:
        n_actually_single = sum(
            1 for v in df_gt1["CCOS_REF_CODE"]
            if len([x.strip() for x in str(v).split(",") if x.strip()]) == 1
        )
        print(f"\n  [A4] Baris berlabel 'fac code > 1' tapi CCOS_REF_CODE sebenarnya 1 code: {n_actually_single:,}")

    # -- A5: POLIS/SLIP yang paling sering menyebabkan multi-match
    if "POLIS_CLN" in df_gt1.columns:
        print(f"\n  [A5] Top 15 POLIS yang paling sering fac code > 1:")
        print(SEP2)
        pc = df_gt1["POLIS_CLN"].value_counts().head(15)
        for val, cnt in pc.items():
            if str(val).strip():
                print(f"    {str(val)[:50]:<52}: {cnt:,}")

    if "SLIP_NO_CLN" in df_gt1.columns:
        print(f"\n  [A6] Top 15 SLIP yang paling sering fac code > 1:")
        print(SEP2)
        sc = df_gt1["SLIP_NO_CLN"].value_counts().head(15)
        for val, cnt in sc.items():
            if str(val).strip():
                print(f"    {str(val)[:50]:<52}: {cnt:,}")


# =============================================================================
# [B] ANALISIS OSBAL: berapa FAC CODE yang memiliki polis/slip yang overlap?
# =============================================================================

def analyze_osbal_overlap(df_osbal):
    """Temukan polis/slip di OSBAL yang muncul di lebih dari 1 FAC CODE."""
    print(f"\n{SEP}")
    print("  [B] ANALISIS OSBAL: polis/slip yang overlap di banyak FAC CODE")
    print(SEP)

    polis_cols = [c for c in df_osbal.columns if str(c).lower().startswith("clean polis")]
    slip_cols  = [c for c in df_osbal.columns if str(c).lower().startswith("clean slip")]
    print(f"  Clean polis cols: {polis_cols}")
    print(f"  Clean slip  cols: {slip_cols}")

    # CLSDT_POLICY_NO juga ikut
    if "CLSDT_POLICY_NO" in df_osbal.columns:
        polis_cols = ["CLSDT_POLICY_NO"] + polis_cols

    # Build: polis → set of fac codes
    polis_to_facs: dict = {}
    slip_to_facs: dict  = {}

    for _, row in df_osbal.iterrows():
        fac = norm(row.get(OSBAL_FACODE_COL, ""))
        if not fac:
            continue
        for col in polis_cols:
            val = norm(row.get(col, ""))
            if val and len(val) >= 5:
                for v in [x.strip() for x in val.split(",")]:
                    if v:
                        polis_to_facs.setdefault(v, set()).add(fac)
        for col in slip_cols:
            val = norm(row.get(col, ""))
            if val and len(val) >= 7:
                for v in [x.strip() for x in val.split(",")]:
                    if v:
                        slip_to_facs.setdefault(v, set()).add(fac)

    # Polis yang punya > 1 fac code
    ambiguous_polis = {k: v for k, v in polis_to_facs.items() if len(v) > 1}
    ambiguous_slip  = {k: v for k, v in slip_to_facs.items()  if len(v) > 1}

    print(f"\n  Total polis unik di index OSBAL          : {len(polis_to_facs):,}")
    print(f"  Polis yang muncul di > 1 FAC CODE        : {len(ambiguous_polis):,}  ← akar masalah!")
    print(f"  Total slip unik di index OSBAL           : {len(slip_to_facs):,}")
    print(f"  Slip yang muncul di > 1 FAC CODE         : {len(ambiguous_slip):,}")

    # Polis dengan paling banyak fac code
    if ambiguous_polis:
        sorted_ap = sorted(ambiguous_polis.items(), key=lambda x: len(x[1]), reverse=True)
        print(f"\n  [B1] Top 20 polis dengan paling banyak FAC CODE:")
        print(SEP2)
        for polis, facs in sorted_ap[:20]:
            print(f"    {polis[:50]:<52}: {len(facs)} codes → {sorted(facs)[:6]}")

    if ambiguous_slip:
        sorted_as = sorted(ambiguous_slip.items(), key=lambda x: len(x[1]), reverse=True)
        print(f"\n  [B2] Top 20 slip dengan paling banyak FAC CODE:")
        print(SEP2)
        for slip, facs in sorted_as[:20]:
            print(f"    {slip[:50]:<52}: {len(facs)} codes → {sorted(facs)[:6]}")

    # Distribusi: berapa polis punya 2 fac, 3 fac, dsb
    counter_p = collections.Counter(len(v) for v in ambiguous_polis.values())
    counter_s = collections.Counter(len(v) for v in ambiguous_slip.values())
    print(f"\n  [B3] Distribusi #fac code per polis yang ambigu:")
    for n_fac in sorted(counter_p.keys()):
        print(f"    {n_fac} fac codes: {counter_p[n_fac]:,} polis")
    print(f"\n  [B3b] Distribusi #fac code per slip yang ambigu:")
    for n_fac in sorted(counter_s.keys()):
        print(f"    {n_fac} fac codes: {counter_s[n_fac]:,} slip")

    return ambiguous_polis, ambiguous_slip


# =============================================================================
# [C] ANALISIS FACUL: FAC CODE ambigu
# =============================================================================

def analyze_facul_overlap(df_facul):
    """Temukan polis/slip di FACUL yang overlap ke banyak FAC CODE."""
    print(f"\n{SEP}")
    print("  [C] ANALISIS FACUL: polis/slip yang overlap di banyak FAC CODE")
    print(SEP)

    polis_cols = [c for c in df_facul.columns if str(c).lower().startswith("clean polis")]
    slip_cols  = [c for c in df_facul.columns if str(c).lower().startswith("clean slip")]
    if "CLSDT_POLICY_NO" in df_facul.columns:
        polis_cols = ["CLSDT_POLICY_NO"] + polis_cols

    polis_to_facs: dict = {}
    for _, row in df_facul.iterrows():
        fac = norm(row.get(FACUL_FACODE_COL, ""))
        if not fac:
            continue
        for col in polis_cols:
            val = norm(row.get(col, ""))
            if val and len(val) >= 5:
                for v in [x.strip() for x in val.split(",")]:
                    if v:
                        polis_to_facs.setdefault(v, set()).add(fac)

    ambiguous = {k: v for k, v in polis_to_facs.items() if len(v) > 1}
    print(f"  Polis FACUL yang muncul di > 1 FAC CODE  : {len(ambiguous):,}")
    if ambiguous:
        sorted_a = sorted(ambiguous.items(), key=lambda x: len(x[1]), reverse=True)
        print(f"\n  Top 10 polis FACUL ambigu:")
        for polis, facs in sorted_a[:10]:
            print(f"    {polis[:50]:<52}: {len(facs)} codes → {sorted(facs)[:5]}")

    return ambiguous


# =============================================================================
# [D] PROFILING: perkiraan waktu per tahap
# =============================================================================

def analyze_performance():
    """Analisis bottleneck performa pipeline."""
    print(f"\n{SEP}")
    print("  [D] ANALISIS PERFORMA: potensi bottleneck")
    print(SEP)

    print("""
  Bottleneck yang ditemukan dari analisis kode:

  1. [BESAR] cleaning_facul.py / cleaning_osbal.py — df.iterrows() baris per baris
     - Kode menggunakan for-loop row-by-row dengan iterrows()
     - Untuk data 100k+ baris ini sangat lambat (vs vectorized pandas)
     - Estimasi: 3-10x lebih lambat dari vectorized pandas

  2. [BESAR] prod_sus_1.py / prod_sus_2.py — LIKE match O(n*m) per baris
     - Stage 2 LIKE match: untuk setiap baris suspend, iterasi kandidat
     - _like_match() harus cek setiap kandidat di token_index → bisa ribuan

  3. [SEDANG] cleaning_osbal.py — .iterrows() dengan CLSDT logic
     - Setiap baris: clean CLSDT dulu, jika tidak valid fallback ke FAC
     - Ini wajar, tapi iterrows overhead besar

  4. [SEDANG] pd.read_excel() tanpa cache → sangat lambat untuk file besar
     - osbal.xlsx: ~70 MB, facul.xlsx: ~88 MB
     - Solusi: cache pickle sudah ada, TAPI cache harus valid

  5. [KECIL] pd.to_datetime() dipanggil per-baris di loop matching
     - Setiap baris, parsing tanggal dilakukan 1-2x via try/except
     - Sebaiknya pre-parse semua tanggal sebelum loop

  6. [KECIL] _narrow_by_periode() → pd.to_datetime() dalam loop kandidat
     - Untuk setiap kandidat OSBAL, parse tanggal dari raw value
     - Jika ada 50 kandidat × N suspend rows = banyak parse
    """)

    print("  File sizes (data aktual):")
    for f, label in [
        ("data/facul.xlsx",             "facul.xlsx (raw)"),
        ("data/facul_clean_aca.xlsx",   "facul_clean_aca.xlsx"),
        ("data/osbal.xlsx",             "osbal.xlsx (raw)"),
        ("data/osbal_clean_aca.xlsx",   "osbal_clean_aca.xlsx"),
        ("data/suspend_clean_aca.xlsx", "suspend_clean_aca.xlsx"),
        ("data/ri slip.xlsx",           "ri slip.xlsx"),
    ]:
        if os.path.exists(f):
            mb = os.path.getsize(f) / 1024 / 1024
            cache = f + ".cache.pkl"
            cache_ok = " [cache OK]" if (os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(f)) else " [NO CACHE]"
            print(f"    {label:<35}: {mb:>8.1f} MB{cache_ok}")


# =============================================================================
# [E] SIMULASI: akumulasi fac code — apakah bisa dikurangi?
# =============================================================================

def simulate_accumulation_reduction(df_osbal):
    """
    Simulasi: berapa banyak multi-fac-code yang bisa diselesaikan
    dengan strategi tambahan (misalnya: narrowing by currency lebih agresif,
    atau narrow by periode).
    """
    print(f"\n{SEP}")
    print("  [E] SIMULASI: strategi mengurangi 'fac code > 1'")
    print(SEP)

    # Temukan FAC CODE di OSBAL yang punya CCOS_CURR
    if "CCOS_CURR" not in df_osbal.columns:
        print("  [!] Kolom CCOS_CURR tidak ada di OSBAL — skip simulasi currency.")
        return

    polis_cols = [c for c in df_osbal.columns if str(c).lower().startswith("clean polis")]
    if "CLSDT_POLICY_NO" in df_osbal.columns:
        polis_cols = ["CLSDT_POLICY_NO"] + polis_cols

    # Bangun: polis → list of (fac, curr, com_date)
    polis_to_info: dict = {}
    for _, row in df_osbal.iterrows():
        fac  = norm(row.get(OSBAL_FACODE_COL, ""))
        curr = norm(row.get("CCOS_CURR", ""))
        com_date = row.get("FAC_COM_DATE", None)
        if not fac:
            continue
        for col in polis_cols:
            val = norm(row.get(col, ""))
            if val and len(val) >= 5:
                for v in [x.strip() for x in val.split(",")]:
                    if v:
                        polis_to_info.setdefault(v, []).append({
                            "fac": fac, "curr": curr, "com_date": com_date
                        })

    # Kasus yang ambigu (> 1 fac)
    ambiguous = {k: v for k, v in polis_to_info.items() if len({x["fac"] for x in v}) > 1}
    print(f"  Polis ambigu (> 1 fac): {len(ambiguous):,}")

    can_resolve_by_currency = 0
    can_resolve_by_period   = 0
    still_ambiguous         = 0

    for polis, infos in ambiguous.items():
        facs = {x["fac"] for x in infos}
        currs = {x["curr"]: set() for x in infos}
        for info in infos:
            currs[info["curr"]].add(info["fac"])

        # Jika currency memisahkan fac code → bisa resolve saat currency diketahui
        if len(currs) > 1:
            can_resolve_by_currency += 1
        else:
            # Coba periode
            dates = set()
            for info in infos:
                if info["com_date"] and not (isinstance(info["com_date"], float) and pd.isna(info["com_date"])):
                    dates.add(str(info["com_date"])[:7])  # year-month
            if len(dates) > 1:
                can_resolve_by_period += 1
            else:
                still_ambiguous += 1

    print(f"\n  Dari {len(ambiguous):,} polis ambigu:")
    print(f"    Bisa resolve dengan filter CURRENCY     : {can_resolve_by_currency:,}")
    print(f"    Bisa resolve dengan filter PERIODE      : {can_resolve_by_period:,}")
    print(f"    Tetap ambigu (currency & periode sama)  : {still_ambiguous:,}  ← harus diatasi di data source")

    pct_resolvable = (can_resolve_by_currency + can_resolve_by_period) / len(ambiguous) * 100 if ambiguous else 0
    print(f"\n  Total yang potensial bisa di-resolve     : {pct_resolvable:.1f}%")
    print(f"""
  KESIMPULAN STRATEGI:
  - {can_resolve_by_currency:,} kasus bisa di-resolve HANYA jika currency suspend diketahui
    dan currency narrowing diterapkan SEBELUM ada match.
  - Kode saat ini sudah punya currency narrowing (ATURAN 1), TAPI hanya aktif
    saat ada > 1 kandidat setelah match. Sudah benar.
  - {still_ambiguous:,} kasus adalah genuinely ambigu di level data OSBAL
    (polis yang sama, currency sama, periode sama → beda fac code).
    Ini adalah masalah data, BUKAN masalah kode.
    """)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"\n{SEP}")
    print("  INVESTIGASI: FAC CODE > 1 & PERFORMA PIPELINE")
    print(SEP)

    # [0] Load data
    print("\n[0] Loading data ...", flush=True)
    df_osbal = load_pkl(OSBAL_FILE,   "OSBAL")
    df_facul = load_pkl(FACUL_FILE,   "FACUL")

    # [A] Analisis output
    print("\n[0b] Loading output files ...", flush=True)
    df_v1    = load_output(OUTPUT_V1,    "final_output_v1")
    df_v2    = load_output(OUTPUT_V2,    "final_output_v2")
    df_final = load_output(OUTPUT_FINAL, "final_output")

    analyze_facode_gt1(df_v1,    "final_output_v1.xlsx (row asli)")
    analyze_facode_gt1(df_v2,    "final_output_v2.xlsx (akumulasi)")
    analyze_facode_gt1(df_final, "final_output.xlsx")

    # [B] Analisis OSBAL overlap
    ambig_polis_osbal, ambig_slip_osbal = analyze_osbal_overlap(df_osbal)

    # [C] Analisis FACUL overlap
    analyze_facul_overlap(df_facul)

    # [D] Performa
    analyze_performance()

    # [E] Simulasi
    simulate_accumulation_reduction(df_osbal)

    print(f"\n{SEP}")
    print("  SELESAI — lihat laporan di atas")
    print(SEP)


if __name__ == "__main__":
    main()
