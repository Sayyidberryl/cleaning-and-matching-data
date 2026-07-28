"""
main.py
=======
Flow final: Matching & Join hasil cleaning tiga tabel.

Urutan matching:
  1. Suspend  →  OSBAL
  2. Suspend  →  FACUL  (jika tidak ditemukan di OSBAL)

Setelah matching → narrowing pasangan → flagging → perhitungan → join → output.

Kolom referensi:
  SUSPEND  : RECEIPT NO, CREDIT NOTES, DETAIL RINCIAN NO, RECEIPT DATE,
             CEDANT NAME, CEDANT SHRT NAME,
             insured_ori, clean insured 1..6,
             CURR ORI, AMOUNT ORI, CURR PAY, AMOUNT PAY,
             polis_ori, clean polis 1,
             slip_ori,  clean slip 1,
             DESC 1..4, STATUS, REC_TYPE,
             CEK FASE SAS, Mark Data to SAS

  OSBAL    : CCOS_DOC_NO, CCOS_DATE, CCOS_REF_CODE, CCOS_COMP, CCOS_COMP_NAME,
             CCOS_REF_COMP, CCOS_REF_COMP_NAME,
             insured_ori, clean insured 1..5,
             CCOS_CURR, CCOS_OR_BAL, CCOS_BAL_DUE,
             CCOS_OR_BAL_IN_IDR, CCOS_BAL_DUE_IN_IDR,
             FAC_COM_DATE, FAC_EXP_DATE, FAC_DUE_DATES, FAC_SUB_CLASS,
             polis_ori, clean polis 1..5,
             slip_ori,  clean slip 1..5,
             CLASS_CODE, CLASS_NAME

  FACUL    : FAC_CODE, FAC_CEDANT, COMP_NAME, FAC_BROKER, COMP_NAME2,
             mitra_bisnis,
             insured_ori, clean insured 1..5,
             polis_ori, clean polis 1..12,
             slip_ori,  clean slip 1..5,
             FAC_CURRENCY, FAC_COM_DATE, FAC_EXP_DATE, FAC_SUB_CLASS,
             FAC_RISK, FAC_DESC, FAC_ACC_STS, FAC_STS_SLIP
"""

import os
import re

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# PATHS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SUSPEND_FILE = os.path.join("data", "suspend_clean_aca.xlsx")
OSBAL_FILE   = os.path.join("data", "osbal_clean_aca.xlsx")
FACUL_FILE   = os.path.join("data", "facul_clean_aca.xlsx")
OUTPUT_FILE  = os.path.join("data", "final_output.xlsx")

# Kolom FAC code per sumber
OSBAL_FACODE_COL = "CCOS_REF_CODE"
FACUL_FACODE_COL = "FAC_CODE"

# Urutan kolom output final
FINAL_COLUMNS = [
    "CCOS_DOC_NO",
    "CCOS_REF_CODE",
    "RECEIPT NO",
    "CREDIT NOTES",
    "DETAIL RINCIAN NO",
    "RECEIPT DATE",
    "CEDANT NAME",
    "CEDANT SHRT NAME",
    "INSURED_ORI",
    "INSURED_1",
    "INSURED_2",
    "CURR ORI",
    "AMOUNT ORI",
    "AMOUNT_ORI_MIN1",
    "CURR PAY",
    "AMOUNT PAY",
    "CCOS_OR_BAL",
    "CCOS_BAL_DUE",
    "DIFERENCE",
    "FLAG_PROD",
    "POLIS_ORI",
    "POLIS_CLN",
    "SLIP_NO_ORI",
    "SLIP_NO_CLN",
    "DESC 1",
    "DESC 2",
    "DESC 3",
    "DESC 4",
    "STATUS",
    "REC_TYPE",
    "CEK AMOUNT DATABASE X BAL RV",
    "Mark Admin Fac Code",
    "Mark Admin",
    "Mark Admin (Status)",
    "Mark ARP",
    "SKENARIO",
]


# ─────────────────────────────────────────────────────────────────────────────
# NORMALISASI & KOLOM CLEAN
# ─────────────────────────────────────────────────────────────────────────────

def _norm(val) -> str:
    """Normalisasi nilai → string uppercase, spasi tunggal."""
    if pd.isna(val) or val is None:
        return ""
    return re.sub(r"\s+", " ", str(val).strip().upper())


def _get_clean_cols(df: pd.DataFrame, prefix: str) -> list:
    """Ambil semua nama kolom yang diawali prefix (case-insensitive)."""
    return [c for c in df.columns if c.lower().startswith(prefix.lower())]


def _row_clean_vals(row: pd.Series, clean_cols: list) -> list:
    """Kumpulkan nilai unik non-kosong dari kolom-kolom clean pada satu baris."""
    seen = []
    for col in clean_cols:
        v = _norm(row.get(col, ""))
        if v and v not in seen:
            seen.append(v)
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# BUILD LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def _build_multi_lookup(df: pd.DataFrame, clean_cols: list) -> dict:
    """Lookup dari semua kolom clean: normalized_val → [row_indices]."""
    lookup: dict = {}
    for idx, row in df.iterrows():
        for col in clean_cols:
            v = _norm(row.get(col, ""))
            if v:
                lookup.setdefault(v, []).append(idx)
    return lookup


def _build_ori_lookup(df: pd.DataFrame, ori_col: str) -> dict:
    """Lookup dari kolom ori: normalized_val → [row_indices]."""
    lookup: dict = {}
    for idx, row in df.iterrows():
        v = _norm(row.get(ori_col, ""))
        if v:
            lookup.setdefault(v, []).append(idx)
    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING
# ─────────────────────────────────────────────────────────────────────────────

def _match_row(
    sus_row: pd.Series,
    lkp_slip_clean:    dict,
    lkp_polis_clean:   dict,
    lkp_insured_clean: dict,
    lkp_slip_ori:      dict,
    lkp_polis_ori:     dict,
    lkp_insured_ori:   dict,
    sus_polis_clean_cols:   list,
    sus_slip_clean_cols:    list,
    sus_insured_clean_cols: list,
) -> tuple:
    """
    Matching satu baris suspend ke referensi — 6 skenario berurutan:
      1. slip clean   2. polis clean   3. insured clean
      4. slip ori     5. polis ori     6. insured ori

    Returns: (matched_indices: list[int], skenario: str)
    """
    scenarios = [
        (_row_clean_vals(sus_row, sus_slip_clean_cols),    lkp_slip_clean,    "SLIP_CLEAN"),
        (_row_clean_vals(sus_row, sus_polis_clean_cols),   lkp_polis_clean,   "POLIS_CLEAN"),
        (_row_clean_vals(sus_row, sus_insured_clean_cols), lkp_insured_clean, "INSURED_CLEAN"),
        ([_norm(sus_row.get("slip_ori", ""))],             lkp_slip_ori,      "SLIP_ORI"),
        ([_norm(sus_row.get("polis_ori", ""))],            lkp_polis_ori,     "POLIS_ORI"),
        ([_norm(sus_row.get("insured_ori", ""))],          lkp_insured_ori,   "INSURED_ORI"),
    ]

    for sus_vals, lookup, label in scenarios:
        matched = {idx for v in sus_vals if v and v in lookup for idx in lookup[v]}
        if matched:
            return list(matched), label

    return [], "UNMATCHED"


# ─────────────────────────────────────────────────────────────────────────────
# NARROWING
# ─────────────────────────────────────────────────────────────────────────────

def _ref_has_any(ref_row: pd.Series, ref_clean_cols: list, ori_col: str, sus_vals: list) -> bool:
    """Cek apakah baris referensi memiliki minimal satu nilai dari sus_vals."""
    if not sus_vals:
        return False
    ref_ori = _norm(ref_row.get(ori_col, ""))
    ref_vals = set(_row_clean_vals(ref_row, ref_clean_cols))
    if ref_ori:
        ref_vals.add(ref_ori)
    return bool(set(sus_vals) & ref_vals)


def _all_sus_vals(sus_row: pd.Series, clean_cols: list, ori_col: str) -> list:
    """Gabungkan semua nilai clean + ori dari baris suspend untuk satu entitas."""
    ori = _norm(sus_row.get(ori_col, ""))
    vals = _row_clean_vals(sus_row, clean_cols)
    if ori:
        vals = list(set(vals + [ori]))
    return vals


def _narrow_by_pair(
    sus_row: pd.Series,
    matched_idx: list,
    df_ref: pd.DataFrame,
    skenario: str,
    ref_polis_clean_cols: list,
    ref_slip_clean_cols:  list,
    sus_polis_clean_cols: list,
    sus_slip_clean_cols:  list,
) -> list:
    """
    Penyempitan hasil matching berpasangan:
    - Matched via SLIP    → tambah filter POLIS
    - Matched via POLIS   → tambah filter SLIP
    - Matched via INSURED → tambah filter POLIS atau SLIP

    Jika narrowing menghasilkan kosong → kembalikan hasil sebelum narrowing.
    """
    if len(matched_idx) <= 1:
        return matched_idx

    sus_polis = _all_sus_vals(sus_row, sus_polis_clean_cols, "polis_ori")
    sus_slip  = _all_sus_vals(sus_row, sus_slip_clean_cols,  "slip_ori")

    def keep(i: int) -> bool:
        ref = df_ref.loc[i]
        polis_ok = _ref_has_any(ref, ref_polis_clean_cols, "polis_ori", sus_polis)
        slip_ok  = _ref_has_any(ref, ref_slip_clean_cols,  "slip_ori",  sus_slip)

        if "SLIP"    in skenario:
            return polis_ok
        if "POLIS"   in skenario:
            return slip_ok
        if "INSURED" in skenario:
            return polis_ok or slip_ok
        return True

    narrowed = [i for i in matched_idx if keep(i)]
    return narrowed if narrowed else matched_idx


# ─────────────────────────────────────────────────────────────────────────────
# KOLOM TURUNAN
# ─────────────────────────────────────────────────────────────────────────────

def _compute_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Hitung AMOUNT_ORI_MIN1, DIFERENCE, dan FLAG_PROD."""
    amt_ori  = pd.to_numeric(df.get("AMOUNT ORI",   0), errors="coerce").fillna(0)
    bal_due  = pd.to_numeric(df.get("CCOS_BAL_DUE", 0), errors="coerce").fillna(0)
    facode_s = df.get("Mark Admin Fac Code", pd.Series("", index=df.index)).fillna("")

    df["AMOUNT_ORI_MIN1"] = amt_ori * -1
    df["DIFERENCE"]       = df["AMOUNT_ORI_MIN1"] - bal_due

    a_min1 = df["AMOUNT_ORI_MIN1"]
    df["FLAG_PROD"] = np.select(
        [
            facode_s.str.strip() == "facode lebih dari 1",
            (a_min1 == bal_due) | (a_min1 < bal_due),
            (a_min1 > bal_due)  | ((a_min1 != 0) & (bal_due == 0)),
        ],
        ["Matching >1 fac code", "Adjustment", "New Entry"],
        default="Unmatching",
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

def _load_excel(path: str, label: str) -> pd.DataFrame:
    print(f"  Membaca {label}: {path} ...")
    df = pd.read_excel(path)
    print(f"  -> {len(df):,} baris, {len(df.columns)} kolom")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING SATU SUMBER
# ─────────────────────────────────────────────────────────────────────────────

def _build_lookups(df: pd.DataFrame, polis_cols: list, slip_cols: list, insured_cols: list) -> tuple:
    """Bangun 6 lookup (clean + ori) untuk satu DataFrame referensi."""
    return (
        _build_multi_lookup(df, slip_cols),
        _build_multi_lookup(df, polis_cols),
        _build_multi_lookup(df, insured_cols),
        _build_ori_lookup(df, "slip_ori"),
        _build_ori_lookup(df, "polis_ori"),
        _build_ori_lookup(df, "insured_ori"),
    )


def _try_match(
    sus_row: pd.Series,
    df_ref: pd.DataFrame,
    lookups: tuple,
    ref_polis_cols: list,
    ref_slip_cols:  list,
    sus_polis_cols: list,
    sus_slip_cols:  list,
    sus_insured_cols: list,
) -> tuple:
    """
    Coba match satu baris suspend ke satu sumber referensi.
    Returns: (matched_idx: list, skenario: str)
    """
    lkp_slip_cln, lkp_polis_cln, lkp_ins_cln, lkp_slip_ori, lkp_polis_ori, lkp_ins_ori = lookups

    m_idx, m_sce = _match_row(
        sus_row,
        lkp_slip_cln, lkp_polis_cln, lkp_ins_cln,
        lkp_slip_ori, lkp_polis_ori, lkp_ins_ori,
        sus_polis_cols, sus_slip_cols, sus_insured_cols,
    )

    if m_idx:
        m_idx = _narrow_by_pair(
            sus_row, m_idx, df_ref, m_sce,
            ref_polis_cols, ref_slip_cols,
            sus_polis_cols, sus_slip_cols,
        )

    return m_idx, m_sce


# ─────────────────────────────────────────────────────────────────────────────
# BANGUN BARIS OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_ccos(ref_rows: list) -> dict:
    """Akumulasikan nilai CCOS dari baris-baris OSBAL yang matched."""
    def join_str(key):
        return ", ".join(filter(None, (str(r.get(key, "")) for r in ref_rows)))

    def sum_num(key):
        return sum(pd.to_numeric(r.get(key, 0), errors="coerce") or 0 for r in ref_rows)

    return {
        "CCOS_DOC_NO":  join_str("CCOS_DOC_NO"),
        "CCOS_REF_CODE": join_str("CCOS_REF_CODE"),
        "CCOS_OR_BAL":  sum_num("CCOS_OR_BAL"),
        "CCOS_BAL_DUE": sum_num("CCOS_BAL_DUE"),
    }


def _get_facode_mark(ref_rows: list, source: str) -> str:
    """Tentukan label facode dari hasil matching."""
    if not ref_rows or not ref_rows[0]:
        return ""
    facode_col = OSBAL_FACODE_COL if source == "OSBAL" else FACUL_FACODE_COL
    facodes = {
        str(r.get(facode_col, "")).strip()
        for r in ref_rows
        if str(r.get(facode_col, "")).strip()
    }
    if len(facodes) > 1:
        return "facode lebih dari 1"
    return next(iter(facodes), "")


def _build_output_row(sus_row: pd.Series, source: str, skenario: str, ref_rows: list) -> dict:
    """Susun satu baris output dari data suspend + hasil matching."""
    has_match = bool(source and ref_rows and ref_rows[0])

    if source == "OSBAL" and has_match:
        ccos = _aggregate_ccos(ref_rows)
    else:
        ccos = {"CCOS_DOC_NO": "", "CCOS_REF_CODE": "", "CCOS_OR_BAL": np.nan, "CCOS_BAL_DUE": np.nan}

    facode_mark  = _get_facode_mark(ref_rows, source) if has_match else ""
    full_skenario = f"{source}_{skenario}" if source else "UNMATCHED"

    return {
        # CCOS columns (dari OSBAL)
        "CCOS_DOC_NO":  ccos["CCOS_DOC_NO"],
        "CCOS_REF_CODE": ccos["CCOS_REF_CODE"],

        # Suspend columns
        "RECEIPT NO":        sus_row.get("RECEIPT NO", ""),
        "CREDIT NOTES":      sus_row.get("CREDIT NOTES", ""),
        "DETAIL RINCIAN NO": sus_row.get("DETAIL RINCIAN NO", ""),
        "RECEIPT DATE":      sus_row.get("RECEIPT DATE", ""),
        "CEDANT NAME":       sus_row.get("CEDANT NAME", ""),
        "CEDANT SHRT NAME":  sus_row.get("CEDANT SHRT NAME", ""),

        "INSURED_ORI": sus_row.get("insured_ori", ""),
        "INSURED_1":   sus_row.get("clean insured 1", ""),
        "INSURED_2":   sus_row.get("clean insured 2", ""),

        "CURR ORI":   sus_row.get("CURR ORI", ""),
        "AMOUNT ORI": sus_row.get("AMOUNT ORI", ""),
        "CURR PAY":   sus_row.get("CURR PAY", ""),
        "AMOUNT PAY": sus_row.get("AMOUNT PAY", ""),

        "CCOS_OR_BAL":  ccos["CCOS_OR_BAL"],
        "CCOS_BAL_DUE": ccos["CCOS_BAL_DUE"],

        "POLIS_ORI":   sus_row.get("polis_ori", ""),
        "POLIS_CLN":   sus_row.get("clean polis 1", ""),
        "SLIP_NO_ORI": sus_row.get("slip_ori", ""),
        "SLIP_NO_CLN": sus_row.get("clean slip 1", ""),

        "DESC 1":  sus_row.get("DESC 1", ""),
        "DESC 2":  sus_row.get("DESC 2", ""),
        "DESC 3":  sus_row.get("DESC 3", ""),
        "DESC 4":  sus_row.get("DESC 4", ""),

        "STATUS":   sus_row.get("STATUS", ""),
        "REC_TYPE": sus_row.get("REC_TYPE", ""),

        # Kolom admin (diisi manual)
        "CEK AMOUNT DATABASE X BAL RV": "",
        "Mark Admin Fac Code":          facode_mark,
        "Mark Admin":                   "",
        "Mark Admin (Status)":          "",
        "Mark ARP":                     "",

        "SKENARIO": full_skenario,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESS
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    print("\n" + "=" * 60)
    print("  PRODUCTION SCRIPT - MATCHING & JOIN")
    print("=" * 60)

    # [1] Load data
    print("\n[1/6] Loading data cleaned ...")
    df_sus   = _load_excel(SUSPEND_FILE, "SUSPEND")
    df_osbal = _load_excel(OSBAL_FILE,   "OSBAL")
    df_facul = _load_excel(FACUL_FILE,   "FACUL")

    # [2] Identifikasi kolom clean
    print("\n[2/6] Identifikasi kolom referensi ...")

    sus_polis_cols   = _get_clean_cols(df_sus, "clean polis")
    sus_slip_cols    = _get_clean_cols(df_sus, "clean slip")
    sus_insured_cols = _get_clean_cols(df_sus, "clean insured")
    print(f"  Suspend -> clean_polis={sus_polis_cols}, clean_slip={sus_slip_cols}")

    osbal_polis_cols   = _get_clean_cols(df_osbal, "clean polis")
    osbal_slip_cols    = _get_clean_cols(df_osbal, "clean slip")
    osbal_insured_cols = _get_clean_cols(df_osbal, "clean insured")
    print(f"  OSBAL   -> clean_polis={osbal_polis_cols}, clean_slip={osbal_slip_cols}")

    facul_polis_cols   = _get_clean_cols(df_facul, "clean polis")
    facul_slip_cols    = _get_clean_cols(df_facul, "clean slip")
    facul_insured_cols = _get_clean_cols(df_facul, "clean insured")
    print(f"  FACUL   -> clean_polis={facul_polis_cols}, clean_slip={facul_slip_cols}")

    # [3] Build lookup index
    print("\n[3/6] Membangun lookup index ...")
    osbal_lookups = _build_lookups(df_osbal, osbal_polis_cols, osbal_slip_cols, osbal_insured_cols)
    print("  OSBAL lookup selesai.")
    facul_lookups = _build_lookups(df_facul, facul_polis_cols, facul_slip_cols, facul_insured_cols)
    print("  FACUL lookup selesai.")

    # [4] Matching per baris suspend
    print(f"\n[4/6] Matching {len(df_sus):,} baris suspend ...")

    results = []
    for loop_i, (_, sus_row) in enumerate(df_sus.iterrows(), 1):
        if loop_i % 500 == 0:
            print(f"  Progress: {loop_i:,} / {len(df_sus):,} ...")

        # Coba ke OSBAL
        source, skenario, matched_idx = None, "UNMATCHED", []
        m_idx, m_sce = _try_match(
            sus_row, df_osbal, osbal_lookups,
            osbal_polis_cols, osbal_slip_cols,
            sus_polis_cols, sus_slip_cols, sus_insured_cols,
        )
        if m_idx:
            source, skenario, matched_idx = "OSBAL", m_sce, m_idx

        # Fallback ke FACUL
        if not matched_idx:
            m_idx, m_sce = _try_match(
                sus_row, df_facul, facul_lookups,
                facul_polis_cols, facul_slip_cols,
                sus_polis_cols, sus_slip_cols, sus_insured_cols,
            )
            if m_idx:
                source, skenario, matched_idx = "FACUL", m_sce, m_idx

        df_ref   = df_osbal if source == "OSBAL" else df_facul
        ref_rows = [df_ref.loc[i].to_dict() for i in matched_idx] if matched_idx else [{}]

        results.append(_build_output_row(sus_row, source, skenario, ref_rows))

    # [5] Bangun DataFrame & hitung kolom turunan
    print(f"\n[5/6] Membangun DataFrame output ({len(results):,} baris) ...")
    df_out = pd.DataFrame(results)

    for col in ["AMOUNT ORI", "CCOS_OR_BAL", "CCOS_BAL_DUE"]:
        df_out[col] = pd.to_numeric(df_out[col], errors="coerce")

    df_out = _compute_derived_columns(df_out)
    df_out.loc[df_out["SKENARIO"] == "UNMATCHED", "FLAG_PROD"] = "Unmatching"

    # Pastikan semua kolom final ada
    for col in FINAL_COLUMNS:
        if col not in df_out.columns:
            df_out[col] = ""

    df_out = df_out[FINAL_COLUMNS]

    # [6] Simpan output
    print(f"\n[6/6] Menyimpan hasil ke: {OUTPUT_FILE} ...")
    df_out.to_excel(OUTPUT_FILE, index=False)

    print(f"\n{'=' * 60}")
    print(f"  [OK] SELESAI!")
    print(f"  Total baris output   : {len(df_out):,}")
    print(f"  Total kolom output   : {len(df_out.columns)}")
    print(f"  File disimpan di     : {OUTPUT_FILE}")

    print(f"\n  Ringkasan FLAG_PROD:")
    for flag, cnt in df_out["FLAG_PROD"].value_counts().items():
        print(f"    {flag:<35}: {cnt:,}")

    print(f"\n  Ringkasan SKENARIO:")
    for sce, cnt in df_out["SKENARIO"].value_counts().items():
        print(f"    {sce:<40}: {cnt:,}")

    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()
