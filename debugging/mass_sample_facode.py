# -*- coding: utf-8 -*-
"""
mass_sample_facode.py — Investigasi MASSAL: ambil 100+ sample baris fac code > 1
dan trace secara mendalam MENGAPA tidak bisa di-resolve.
Bandingkan juga dengan baris yang BERHASIL single fac code.

Jalankan: python mass_sample_facode.py
"""
import sys, io, re, os, random, collections
sys.modules['numexpr']    = None
sys.modules['bottleneck'] = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

random.seed(42)

OSBAL_FILE   = os.path.join("data", "osbal_clean_aca.xlsx")
SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")
OUTPUT_FILE  = os.path.join("data", "final_output_v1.xlsx")  # row-level, lebih detail

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
    print(f"  {label}: excel ...", flush=True)
    return pd.read_excel(path)

print(f"\n{SEP}")
print("  INVESTIGASI MASSAL: Sample 100+ baris fac code > 1")
print(SEP)

print("\n[0] Loading ...")
df_osbal  = load_pkl(OSBAL_FILE,  "OSBAL")
df_sus    = load_pkl(SUSPEND_FILE,"SUSPEND")
df_out    = pd.read_excel(OUTPUT_FILE)
print(f"  Output: {len(df_out):,} rows, {len(df_out.columns)} cols")
print(f"  Cols output: {list(df_out.columns)}")

# ── Build OSBAL index per fac code (slip → fac) ──────────────────────────────
polis_osl = ["CLSDT_POLICY_NO"] + [c for c in df_osbal.columns if str(c).lower().startswith("clean polis")]
slip_osl  = [c for c in df_osbal.columns if str(c).lower().startswith("clean slip")]
if "CLSDT_SLIP_NO" in df_osbal.columns and "CLSDT_SLIP_NO" not in slip_osl:
    slip_osl = ["CLSDT_SLIP_NO"] + slip_osl

print("\n[1] Building OSBAL lookup ...", flush=True)
# slip → set of fac codes
slip_to_facs: dict = {}
polis_to_facs: dict = {}
for _, row in df_osbal.iterrows():
    fac  = norm(row.get("CCOS_REF_CODE", ""))
    curr = norm(row.get("CCOS_CURR", ""))
    if not fac:
        continue
    for col in slip_osl:
        v = norm(row.get(col, ""))
        if v and len(v) >= 7:
            slip_to_facs.setdefault(v, set()).add(fac)
    for col in polis_osl:
        v = norm(row.get(col, ""))
        if v and len(v) >= 5:
            polis_to_facs.setdefault(v, set()).add(fac)

print(f"  Slip index: {len(slip_to_facs):,} entries")
print(f"  Polis index: {len(polis_to_facs):,} entries")

# ── Pisahkan output ──────────────────────────────────────────────────────────
print("\n[2] Separating output ...", flush=True)

def get_mark(row):
    return norm(row.get("Mark Admin Fac Code", ""))

gt1_rows  = df_out[df_out["Mark Admin Fac Code"].astype(str).str.strip() == "facode lebih dari 1"]
ok_rows   = df_out[df_out["Mark Admin Fac Code"].astype(str).str.strip() != "facode lebih dari 1"]

print(f"  Fac code > 1 : {len(gt1_rows):,}")
print(f"  Single/lain  : {len(ok_rows):,}")

# ── Kategorisasi sample: MENGAPA fac code > 1? ──────────────────────────────
print(f"\n{SEP}")
print(f"[3] KATEGORISASI MENDALAM: 150 sample dari fac code > 1")
print(SEP)

sample_indices = random.sample(list(gt1_rows.index), min(150, len(gt1_rows)))
samples = df_out.loc[sample_indices]

categories = collections.Counter()
slip_col_out   = "SLIP_NO_CLN"  if "SLIP_NO_CLN"  in df_out.columns else "clean slip 1"
polis_col_out  = "POLIS_CLN"    if "POLIS_CLN"     in df_out.columns else "clean polis 1"
skenario_col   = "SKENARIO"     if "SKENARIO"       in df_out.columns else None

detail_log = []

for _, row in samples.iterrows():
    slip   = norm(row.get(slip_col_out, ""))
    polis  = norm(row.get(polis_col_out, ""))
    curr   = norm(row.get("CURR ORI", ""))
    sce    = norm(row.get(skenario_col, "")) if skenario_col else ""
    raw_fac = str(row.get("CCOS_REF_CODE", ""))
    fac_codes_out = [x.strip() for x in raw_fac.split(",") if x.strip()]

    # Cek slip: berapa fac code yang match via slip di OSBAL?
    slip_vals = [s.strip() for s in slip.split(",") if s.strip()] if slip else []
    facs_via_slip = set()
    for sv in slip_vals:
        facs_via_slip |= slip_to_facs.get(sv, set())

    # Cek polis: berapa fac code yang match via polis di OSBAL?
    polis_vals = [p.strip() for p in polis.split(",") if p.strip()] if polis else []
    facs_via_polis = set()
    for pv in polis_vals:
        facs_via_polis |= polis_to_facs.get(pv, set())

    n_fac = len(fac_codes_out)
    n_slip_fac = len(facs_via_slip)
    n_polis_fac = len(facs_via_polis)

    # Kategorisasi
    if n_slip_fac == 1:
        cat = "SLIP_UNIQUELY_IDENTIFIES_FAC"  # slip sudah unik, tapi output masih > 1 ← BUG?
    elif n_slip_fac > 1 and n_slip_fac < n_polis_fac:
        cat = "SLIP_NARROWS_BUT_STILL_GT1"
    elif not slip_vals or n_slip_fac == 0:
        if n_polis_fac == 1:
            cat = "POLIS_UNIQUELY_IDENTIFIES_FAC"  # polis sudah unik ← BUG?
        elif n_polis_fac > 1:
            cat = "BOTH_AMBIGUOUS_NO_SLIP"
        else:
            cat = "NO_MATCH_FOUND"
    else:
        cat = "GENUINELY_AMBIGUOUS"

    categories[cat] += 1
    detail_log.append({
        "polis": polis[:50] if polis else "",
        "slip": slip[:40] if slip else "",
        "curr": curr,
        "skenario": sce,
        "n_fac_out": n_fac,
        "facs_out": fac_codes_out[:5],
        "n_slip_fac": n_slip_fac,
        "facs_via_slip": sorted(facs_via_slip)[:5],
        "n_polis_fac": n_polis_fac,
        "cat": cat,
    })

print(f"\nKATEGORI (dari 150 sample):")
print(SEP2)
for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
    pct = cnt / len(detail_log) * 100
    print(f"  {cat:<45}: {cnt:>4} ({pct:.1f}%)")

# ── Detail per kategori ──────────────────────────────────────────────────────
for target_cat in ["SLIP_UNIQUELY_IDENTIFIES_FAC", "POLIS_UNIQUELY_IDENTIFIES_FAC",
                   "SLIP_NARROWS_BUT_STILL_GT1", "BOTH_AMBIGUOUS_NO_SLIP"]:
    matches = [d for d in detail_log if d["cat"] == target_cat]
    if not matches:
        continue
    print(f"\n{SEP}")
    print(f"  [{target_cat}] — {len(matches)} sample")
    print(SEP)
    for d in matches[:8]:
        print(f"  Polis  : {d['polis']}")
        print(f"  Slip   : {d['slip']}")
        print(f"  Curr   : {d['curr']}  |  Skenario: {d['skenario']}")
        print(f"  Output fac codes ({d['n_fac_out']}): {d['facs_out']}")
        print(f"  Via SLIP in OSBAL ({d['n_slip_fac']}): {d['facs_via_slip']}")
        print(f"  Via POLIS in OSBAL ({d['n_polis_fac']}): {d['facs_out'][:3]}...")
        print(f"  {SEP2}")

# ── Bandingkan dengan yang BERHASIL single fac code ──────────────────────────
print(f"\n{SEP}")
print(f"[4] PERBANDINGAN: baris yang BERHASIL single fac code")
print(SEP)

ok_sample = ok_rows[~ok_rows["Mark Admin Fac Code"].astype(str).str.contains("Unmatching|nan", na=True)]
ok_sample = ok_sample.sample(min(50, len(ok_sample)), random_state=42) if len(ok_sample) > 0 else ok_sample

if skenario_col and len(ok_sample) > 0:
    print(f"\n  Distribusi SKENARIO baris BERHASIL:")
    for sce, cnt in ok_sample[skenario_col].value_counts().items():
        print(f"    {str(sce):<40}: {cnt}")

    # Cek: pada baris yang berhasil, berapa yang slip-nya uniquely identifies fac?
    ok_slip_unique = 0
    ok_polis_unique = 0
    for _, row in ok_sample.iterrows():
        slip  = norm(row.get(slip_col_out, ""))
        polis = norm(row.get(polis_col_out, ""))
        slip_vals = [s.strip() for s in slip.split(",") if s.strip()] if slip else []
        polis_vals = [p.strip() for p in polis.split(",") if p.strip()] if polis else []
        facs_s = set()
        for sv in slip_vals:
            facs_s |= slip_to_facs.get(sv, set())
        facs_p = set()
        for pv in polis_vals:
            facs_p |= polis_to_facs.get(pv, set())
        if len(facs_s) == 1:
            ok_slip_unique += 1
        elif len(facs_p) == 1:
            ok_polis_unique += 1

    print(f"\n  Dari {len(ok_sample)} baris berhasil:")
    print(f"    Slip uniquely identifies fac  : {ok_slip_unique}")
    print(f"    Polis uniquely identifies fac : {ok_polis_unique}")
    print(f"    Lainnya                       : {len(ok_sample) - ok_slip_unique - ok_polis_unique}")

# ── Cek kasus SLIP_UNIQUELY_IDENTIFIES_FAC secara mendalam ───────────────────
slip_unique_cases = [d for d in detail_log if d["cat"] == "SLIP_UNIQUELY_IDENTIFIES_FAC"]
if slip_unique_cases:
    print(f"\n{SEP}")
    print(f"[!!] KRITIS: {len(slip_unique_cases)} kasus di mana SLIP sudah UNIK ke 1 FAC CODE")
    print(f"     tapi output masih 'fac code > 1' — ini indikasi kemungkinan BUG atau")
    print(f"     ada fac code yang tidak match antara output vs OSBAL index!")
    print(SEP)
    for d in slip_unique_cases[:10]:
        print(f"  Polis : {d['polis']}")
        print(f"  Slip  : {d['slip']}")
        print(f"  Output fac ({d['n_fac_out']}): {d['facs_out']}")
        print(f"  Via SLIP → 1 fac : {d['facs_via_slip']}")
        print(f"  Curr: {d['curr']}  Skenario: {d['skenario']}")
        print()

# ── Kesimpulan ────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("[5] KESIMPULAN INVESTIGASI MASSAL")
print(SEP)

total = len(detail_log)
n_potential_bug = categories.get("SLIP_UNIQUELY_IDENTIFIES_FAC", 0) + categories.get("POLIS_UNIQUELY_IDENTIFIES_FAC", 0)
n_genuine       = categories.get("GENUINELY_AMBIGUOUS", 0) + categories.get("BOTH_AMBIGUOUS_NO_SLIP", 0) + categories.get("SLIP_NARROWS_BUT_STILL_GT1", 0)

print(f"\n  Total sample          : {total}")
print(f"  Potensi bug/missed    : {n_potential_bug} ({n_potential_bug/total*100:.1f}%)")
print(f"  Genuinely ambiguous   : {n_genuine} ({n_genuine/total*100:.1f}%)")
print(f"\n  Proyeksi ke {len(gt1_rows):,} baris fac code > 1:")
print(f"    Potensi bisa di-fix : ~{int(n_potential_bug/total*len(gt1_rows)):,} baris")
print(f"    Genuinely ambiguous : ~{int(n_genuine/total*len(gt1_rows)):,} baris")
